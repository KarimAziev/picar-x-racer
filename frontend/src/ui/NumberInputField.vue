<template>
  <Field
    :message="message"
    :label="label"
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
  >
    <InputNumber
      showButtons
      v-tooltip="tooltip"
      :inputId="field"
      :pt="{ pcInput: { id: field } }"
      :class="inputClassName"
      v-model="currentValue"
      :invalid="invalid"
      :step="step"
      :disabled="readonly || disabled"
      :minFractionDigits="minFractionDigits"
      :maxFractionDigits="maxFractionDigits"
      v-bind="{ ...otherAttrs, ...extraProps }"
      @input="handleInput"
      @update:model-value="onUpdate"
      @blur="onBlur"
    />
    <slot></slot>
  </Field>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs, computed } from "vue";
import InputNumber, {
  InputNumberEmitsOptions,
  InputNumberProps,
  InputNumberInputEvent,
} from "primevue/inputnumber";
import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";
import { isString, isNumber } from "@/util/guards";

export interface Props extends FieldProps {
  modelValue?: any;
  invalid?: boolean;
  field?: string;
  inputClassName?: string;
  minFractionDigits?: number;
  maxFractionDigits?: number;
  readonly?: boolean;
  disabled?: boolean;
  tooltip?: string;
  step?: number;
  exclusiveMinimum?: number;
  exclusiveMaximum?: number;
}

const props = withDefaults(defineProps<Props>(), {
  minFractionDigits: 0,
  maxFractionDigits: 3,
  step: 1,
});
const otherAttrs: InputNumberProps = useAttrs();

const currentValue = ref(props.modelValue);

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
  },
);

const extraProps = computed(() => {
  if (!isNumber(props.exclusiveMinimum) || !isNumber(props.exclusiveMaximum)) {
    return;
  }
  const excMin = props.exclusiveMinimum;
  const excMax = props.exclusiveMaximum;
  const increment = isNumber(props.step)
    ? props.step
    : isNumber(props.maxFractionDigits)
      ? Math.pow(10, -props.maxFractionDigits)
      : isNumber(otherAttrs.minFractionDigits)
        ? Math.pow(10, -otherAttrs.minFractionDigits)
        : 0;
  return {
    min: excMin + increment,
    max: excMax - increment,
  };
});

const emit = defineEmits(["update:modelValue", "blur"]);

const handleInput = (event: InputNumberInputEvent) => {
  const value = event.value;
  currentValue.value =
    isString(value) && !Number.isNaN(+value) ? +value : value;
  emit("update:modelValue", currentValue.value);
};

const onUpdate: InputNumberEmitsOptions["update:modelValue"] = (newValue) => {
  emit("update:modelValue", newValue);
};

const onBlur: InputNumberEmitsOptions["blur"] = (newValue) => {
  emit("blur", newValue);
};
</script>
