<template>
  <Field
    :message="message"
    :label="label"
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
  >
    <Select
      :pt="{ input: { id: field, name: field } }"
      :loading="loading"
      :options="options"
      :optionLabel="optionLabel"
      :optionValue="optionValue"
      v-tooltip="tooltipText"
      filter
      autoFilterFocus
      :class="props.inputClassName"
      v-model="currentValue"
      :invalid="invalid"
      :disabled="readonly || disabled"
      v-bind="otherAttrs"
      @update:model-value="onUpdate"
    >
      <template #dropdownicon>
        <i class="pi pi-angle-down" />
      </template>
    </Select>
  </Field>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs, computed } from "vue";
import type { SelectEmitsOptions, SelectProps } from "primevue/select";
import type { Props as FieldProps } from "@/ui/Field.vue";
import Select from "primevue/select";
import Field from "@/ui/Field.vue";

export interface Props extends FieldProps {
  modelValue?: any;
  invalid?: boolean;
  field?: string | number;
  fieldClassName?: string;
  inputClassName?: string;
  simpleOptions?: boolean;
  options: SelectProps["options"];
  optionLabel?: string;
  optionValue?: string;
  readonly?: boolean;
  disabled?: boolean;
  loading?: boolean;
  tooltip?: string;
  tooltipHelp?: string;
}
const props = defineProps<Props>();

const otherAttrs = useAttrs();

const currentValue = ref(props.modelValue);

const optionLabel = computed(() =>
  props.simpleOptions ? undefined : props.optionLabel || "label",
);
const optionValue = computed(() =>
  props.simpleOptions ? undefined : props.optionValue || "value",
);

const tooltipText = computed(() => {
  const { tooltip } = props;
  if (!tooltip || !props.options || !/%s/gim.test(tooltip)) {
    return tooltip;
  }

  const optValue = optionValue.value;
  const optLabel = optionLabel.value;

  if (!optValue || !optLabel) {
    return tooltip.replace("%s", currentValue.value || "None");
  }
  const option = props.options.find(
    (opt) => opt && opt[optValue] === currentValue.value,
  );

  if (!option) {
    return tooltip.replace("%s", "None");
  }
  return tooltip.replace("%s", option[optLabel]);
});

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
  },
);

const emit = defineEmits(["update:modelValue"]);

const onUpdate: SelectEmitsOptions["update:modelValue"] = (newValue) => {
  emit("update:modelValue", newValue);
};
</script>
