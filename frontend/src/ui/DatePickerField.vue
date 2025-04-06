<template>
  <Field
    :message="message"
    :label="label"
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
  >
    <DatePicker
      v-bind="props"
      selectionMode="single"
      v-model:model-value="currentValue"
      @update:model-value="handleUpdateModelValue"
    />
  </Field>
</template>

<script setup lang="ts">
import { ref, watch, defineAsyncComponent } from "vue";
import type {
  DatePickerProps,
  DatePickerEmitsOptions,
} from "primevue/datepicker";
import { isString } from "@/util/guards";
import { Nullable } from "@/util/ts-helpers";
import {
  formatDateTimeToIsoString,
  isoStringToDateTime,
  isDate,
} from "@/util/date";
import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";

const modelValue = defineModel<Nullable<string>>("modelValue", {
  required: true,
});

export interface Props
  extends FieldProps,
    Pick<
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
      | "showButtonBar"
    > {
  invalid?: boolean;
  label?: string;
  field?: string;
  inputClassName?: string;
  readonly?: boolean;
  disabled?: boolean;
  tooltip?: string;
}

const DatePicker = defineAsyncComponent({
  loader: () => import("primevue/datepicker"),
});

const props = withDefaults(defineProps<Props>(), {
  showTime: true,

  showButtonBar: true,
});

const emit = defineEmits(["update:modelValue"]);

const getValue = (newVal: any) =>
  isString(newVal) && newVal.length > 0 ? isoStringToDateTime(newVal) : null;

const currentValue = ref(getValue(modelValue));

watch(
  () => modelValue.value,
  (newVal) => {
    currentValue.value =
      isString(newVal) && newVal.length > 0
        ? isoStringToDateTime(newVal)
        : null;
  },
);

const handleUpdateModelValue: DatePickerEmitsOptions["update:modelValue"] = (
  newValue,
) => {
  const dateStr = isDate(newValue) ? formatDateTimeToIsoString(newValue) : null;
  modelValue.value = dateStr;

  emit("update:modelValue", dateStr);
};
</script>
