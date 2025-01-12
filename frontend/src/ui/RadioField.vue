<template>
  <Field
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :label="label"
    :message="message"
    :layout="layout"
  >
    <div
      v-for="category in options"
      :key="category.label"
      class="flex items-center gap-2"
    >
      <RadioButton
        v-model="selectedCategory"
        name="dynamic"
        :value="category.value"
        @update:model-value="handleUpdateCategory"
      />
      <span>{{ category.label }}</span>
    </div>
    <InputText
      v-if="selectedCategory === 'str'"
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
      v-else-if="selectedCategory === 'int'"
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
import type { FieldLayout } from "@/ui/Field.vue";
import { isNumber, isString } from "@/util/guards";

export type Option = {
  value: string;
  label: string;
};

export type Props = {
  modelValue?: any;
  options: Option[];
  invalid?: boolean;
  message?: string | null;
  label?: string;
  field?: string;
  fieldClassName?: string;
  labelClassName?: string;
  inputClassName?: string;
  readonly?: boolean;
  disabled?: boolean;
  layout?: FieldLayout;
  tooltip?: string;
};

const props = defineProps<Props>();

const selectedCategory = ref(isNumber(props.modelValue) ? "int" : "str");
const otherAttrs = useAttrs();

const currentValue = ref(props.modelValue);

const handleUpdateCategory = (value: string) => {
  selectedCategory.value = value;
  if (value === "int" && isString(currentValue.value)) {
    currentValue.value = null;
  } else if (value === "str" && isNumber(currentValue.value)) {
    currentValue.value = null;
  } else if (
    value === "str" &&
    !currentValue.value &&
    isString(props.modelValue)
  ) {
    currentValue.value = props.modelValue;
  } else if (
    value === "str" &&
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
      selectedCategory.value = "str";
    } else if (isNumber(selectedCategory.value)) {
      selectedCategory.value = "int";
    }
  },
);

const emit = defineEmits(["update:modelValue", "value-change"]);

const onUpdate = (newValue?: string | number) => {
  emit("update:modelValue", newValue);
};
</script>
