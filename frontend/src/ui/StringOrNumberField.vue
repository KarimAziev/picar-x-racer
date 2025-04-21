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
        v-model="selectedCategory"
        name="hextype"
        :value="opt.value"
        @update:model-value="handleUpdateCategory"
      />
      <span>{{ opt.label }}</span>
    </div>
    <InputText
      v-if="selectedCategory === 'string'"
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
      v-else-if="selectedCategory === 'integer'"
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
  { value: "string", label: "String" },
];

const selectedCategory = ref(isNumber(props.modelValue) ? "integer" : "string");
const otherAttrs = useAttrs();

const currentValue = ref(props.modelValue);

const handleUpdateCategory = (value: string) => {
  selectedCategory.value = value;
  if (value === "integer" && isString(currentValue.value)) {
    currentValue.value = null;
  } else if (value === "string" && isNumber(currentValue.value)) {
    currentValue.value = null;
  } else if (
    value === "string" &&
    !currentValue.value &&
    isString(props.modelValue)
  ) {
    currentValue.value = props.modelValue;
  } else if (
    value === "string" &&
    !currentValue.value &&
    isNumber(props.modelValue)
  ) {
    currentValue.value = props.modelValue;
  }
};

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
    if (isString(newVal)) {
      selectedCategory.value = "string";
    } else if (isNumber(selectedCategory.value)) {
      selectedCategory.value = "integer";
    }
  },
);

const emit = defineEmits(["update:modelValue", "value-change"]);

const onUpdate = (newValue?: string | number) => {
  emit("update:modelValue", newValue);
};
</script>
