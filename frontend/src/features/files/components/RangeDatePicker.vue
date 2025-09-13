<template>
  <DatePicker
    v-bind="props"
    selectionMode="range"
    v-model:model-value="dates"
    @update:model-value="handleUpdateModelValue"
  />
</template>

<script setup lang="ts">
import type { FilterField } from "@/features/files/interface";
import { ref, watch } from "vue";
import type {
  DatePickerProps,
  DatePickerEmitsOptions,
} from "primevue/datepicker";
import { FilterMatchMode } from "@/features/files/enums";
import { isArray, isString } from "@/util/guards";

const dateRangeFilter = defineModel<FilterField[]>("dateRangeFilter", {
  required: true,
});

const emit = defineEmits(["update:modelValue"]);

const getDateRangeFilterValue = () =>
  dateRangeFilter.value.flatMap((filter) =>
    isString(filter.value) ? [new Date(filter.value)] : [],
  );

const dates = ref(getDateRangeFilterValue());

watch(
  () => dateRangeFilter.value,
  () => {
    dates.value = getDateRangeFilterValue();
  },
);

const handleUpdateModelValue: DatePickerEmitsOptions["update:modelValue"] = (
  newValue,
) => {
  const [startDate, endDate] = isArray(newValue)
    ? newValue.flatMap((v) => (v ? [v] : []))
    : [];

  if (startDate && endDate) {
    dateRangeFilter.value = [
      {
        value: startDate.toISOString(),
        match_mode: FilterMatchMode.DATE_BEFORE,
      },
      {
        value: startDate.toISOString(),
        match_mode: FilterMatchMode.DATE_AFTER,
      },
    ];
    emit("update:modelValue", dateRangeFilter.value);
  }
};

export interface Props
  extends Pick<
    DatePickerProps,
    | "showIcon"
    | "showTime"
    | "name"
    | "minDate"
    | "maxDate"
    | "disabled"
    | "readonly"
    | "placeholder"
    | "id"
    | "inputId"
  > {}

const props = withDefaults(defineProps<Props>(), {
  showTime: true,
  showIcon: true,
});
</script>

<style scoped lang="scss"></style>
