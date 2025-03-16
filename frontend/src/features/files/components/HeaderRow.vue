<template>
  <header>
    <div class="ml-4" />
    <Checkbox
      v-if="selectable"
      v-model="checkedAll"
      inputId="check-all"
      binary
      @update:model-value="toggleCheckAll"
    />
    <span v-else />
    <template v-for="(group, groupKey) in groups">
      <Column
        v-for="(col, field) in group"
        :key="`${field as string}-column`"
        v-bind="col"
        :field="field as string"
        class="pr-4"
        v-if="filters && groupKey === 'filterable'"
        v-model:filter="
          (
            (filters as FileFilterModel)[
              field as keyof FileFilterModel
            ] as FilterFieldStringArray
          ).value
        "
        v-model:ordering="ordering"
        @update:ordering="handleSort"
        @update:filter="handleUpdateFilter"
      />
      <Column
        v-for="(col, field) in group"
        :key="`${field as string}-column-non-filter`"
        v-bind="col"
        :field="field as string"
        class="pr-4"
        v-else
        v-model:ordering="ordering"
        @update:ordering="handleSort"
        @update:filter="handleUpdateFilter"
      />
    </template>
  </header>
</template>
<script setup lang="ts" generic="DataEntry">
import type {
  OrderingModel,
  FileFilterModel,
  FilterFieldStringArray,
} from "@/features/files/interface";
import Column from "@/features/files/components/Column.vue";
import type { ValueLabelOption } from "@/types/common";
import { TableColumnsConfig } from "@/features/files/components/config";

import type { Props as ColumnProps } from "@/features/files/components/Column.vue";
import { computed } from "vue";

type Props = {
  config: TableColumnsConfig<DataEntry>;
  selectable?: boolean;
  filterOptions?: (string | ValueLabelOption)[];
};

const props = withDefaults(defineProps<Props>(), {
  selectable: true,
});

const ordering = defineModel<OrderingModel>("ordering", { required: true });

const filters = defineModel<FileFilterModel>("filters");
const checkedAll = defineModel<boolean>("checkedAll");
const emit = defineEmits([
  "update:ordering",
  "toggle:checkAll",
  "update:filters",
]);

const toggleCheckAll = (value: boolean) => {
  emit("toggle:checkAll", value);
};

const handleSort = () => {
  emit("update:ordering", ordering.value);
};

const groups = computed(() =>
  (
    Object.entries(props.config) as [
      keyof TableColumnsConfig<DataEntry>,
      ColumnProps,
    ][]
  ).reduce(
    (acc, [key, item]) => {
      if (item.filterOptions) {
        acc.filterable = acc.filterable || {};
        acc.filterable[key] = item;
      } else {
        acc.common = acc.common || {};
        acc.common[key] = item;
      }
      return acc;
    },
    {} as Record<string, TableColumnsConfig<DataEntry>>,
  ),
);

const handleUpdateFilter = () => {
  emit("update:filters", filters.value);
};
</script>
