<template>
  <Cell class="justify-start cursor-pointer">
    <template v-if="options && options.length > 0">
      <MultiSelect
        :pt="{ input: { id: `filter-${field}`, name: `filter-name-${field}` } }"
        :options="options"
        optionLabel="label"
        optionValue="value"
        :placeholder="title"
        class="w-20"
        v-model:model-value="filter"
        @update:model-value="onFilter"
      >
        <template #dropdownicon>
          <i class="pi pi-angle-down" />
        </template>
      </MultiSelect>
      <i @click="onSort" :class="`p-2 pi ${sortIcon}`" v-if="sortIcon" />
    </template>
    <span @click="onSort" v-else-if="sortIcon">
      <span class="font-bold">{{ title }}</span>
      <i :class="`p-2 pi ${sortIcon}`" />
    </span>
    <span class="flex gap-1 items-center" v-else>
      <span class="font-bold">{{ title }}</span>
    </span>
  </Cell>
</template>
<script setup lang="ts">
import { SortDirection, FilterMatchMode } from "@/features/files/enums";
import type { OrderingModel } from "@/features/files/interface";
import { computed } from "vue";
import { ValueLabelOption } from "@/types/common";
import { startCase } from "@/util/str";
import { isString } from "@/util/guards";
import Cell from "@/features/files/components/Cell.vue";

export type Props = {
  title?: string;
  sortable?: boolean;
  field: string;
  match_mode?: FilterMatchMode;
  filterOptions?: (string | ValueLabelOption)[];
};

const props = defineProps<Props>();

const ordering = defineModel<OrderingModel>("ordering", { required: true });
const filter = defineModel<any>("filter");

const emit = defineEmits(["update:ordering", "update:filter"]);

const options = computed(() => {
  if (!props.filterOptions) {
    return null;
  }
  return !props.filterOptions
    ? null
    : props.filterOptions.map((v) =>
        isString(v) ? { value: v, label: startCase(v) } : v,
      );
});

const onSort = () => {
  if (props.field === ordering.value.field) {
    ordering.value.direction =
      ordering.value.direction === SortDirection.ASC
        ? SortDirection.DESC
        : SortDirection.ASC;
  } else {
    ordering.value.direction = SortDirection.ASC;
    ordering.value.field = props.field;
  }

  emit("update:ordering", ordering.value);
};

const onFilter = (value: any) => {
  if (props.match_mode === FilterMatchMode.IN) {
    const nextVal = Array.isArray(value)
      ? value.filter(Boolean)
      : isString(value)
        ? [value]
        : value;
    filter.value = nextVal;

    emit("update:filter", nextVal);
  }
};

const iconsByDirection = {
  [SortDirection.ASC]: "pi-sort-amount-up color-primary",
  [SortDirection.DESC]: "pi-sort-amount-down color-primary",
};

const sortIcon = computed(() =>
  !props.sortable
    ? null
    : ordering.value.field === props.field
      ? iconsByDirection[ordering.value.direction]
      : "pi-sort-alt",
);
</script>
