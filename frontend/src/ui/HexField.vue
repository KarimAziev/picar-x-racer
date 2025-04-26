<template>
  <Field
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :label="label"
    :message="message"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
  >
    <div
      v-for="opt in options"
      :key="opt.label"
      class="flex items-center gap-2"
    >
      <RadioButton
        v-model="valueType"
        name="hex-type"
        :value="opt.value"
        @update:model-value="handleUpdateValueType"
      />
      <span>{{ opt.label }}</span>
    </div>
    <InputText
      v-if="valueType === 'string'"
      v-tooltip="tooltip"
      :inputId="field"
      :pt="{ pcInput: { id: field } }"
      :class="props.inputClassName"
      v-model="currentValue"
      :invalid="invalid"
      :disabled="readonly || disabled"
      v-bind="otherAttrs"
      @update:model-value="onUpdate"
    />
    <InputNumber
      v-else-if="valueType === 'integer'"
      showButtons
      v-tooltip="tooltip"
      :inputId="field"
      :pt="{ pcInput: { id: field } }"
      :class="props.inputClassName"
      v-model="currentValue"
      :invalid="invalid"
      :disabled="readonly || disabled"
      v-bind="otherAttrs"
      @update:model-value="onUpdate"
    />
  </Field>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs } from "vue";
import InputText from "primevue/inputtext";
import RadioButton from "primevue/radiobutton";
import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";
import { isNumber, isString } from "@/util/guards";
import { isHexString, hexToDecimal, decimalToHexString } from "@/util/hex";

export type Option = {
  value: string;
  label: string;
};

export interface Props extends FieldProps {
  modelValue?: any;
  invalid?: boolean;
  label?: string;
  field?: string;
  inputClassName?: string;
  readonly?: boolean;
  disabled?: boolean;
  tooltip?: string;
}

const props = defineProps<Props>();

const options: Option[] = [
  { value: "integer", label: "Integer" },
  { value: "string", label: "Hex string" },
];

const valueType = ref(isNumber(props.modelValue) ? "integer" : "string");
const otherAttrs = useAttrs();

const currentValue = ref(props.modelValue);

const stringToNumber = (value: string) => {
  const re = /(\d+)$/;
  const match = value.match(re);
  return match ? +match[1] : null;
};

const handleUpdateValueType = (value: string) => {
  valueType.value = value;
  if (value === "integer" && isString(currentValue.value)) {
    currentValue.value = isHexString(currentValue.value)
      ? hexToDecimal(currentValue.value)
      : stringToNumber(currentValue.value);
  } else if (value === "string" && isNumber(currentValue.value)) {
    currentValue.value = decimalToHexString(currentValue.value);
  } else if (value === "string" && !currentValue.value) {
    currentValue.value = isNumber(props.modelValue)
      ? decimalToHexString(props.modelValue)
      : isString(props.modelValue)
        ? props.modelValue
        : null;
  } else if (value === "integer" && !currentValue.value) {
    currentValue.value = isNumber(props.modelValue)
      ? props.modelValue
      : isHexString(props.modelValue)
        ? hexToDecimal(props.modelValue)
        : isString(props.modelValue)
          ? stringToNumber(props.modelValue)
          : null;
  }
};

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
    if (isString(newVal)) {
      valueType.value = "string";
    } else if (isNumber(newVal)) {
      valueType.value = "integer";
    }
  },
);

const emit = defineEmits(["update:modelValue", "value-change"]);

const onUpdate = (newValue?: string | number) => {
  emit("update:modelValue", newValue);
};
</script>
