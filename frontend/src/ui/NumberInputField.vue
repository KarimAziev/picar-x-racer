<template>
  <Field
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :label="label"
    :message="message"
    :layout="layout"
  >
    <InputNumber
      showButtons
      v-tooltip="tooltip"
      :inputId="field"
      :pt="{ pcInput: { id: field } }"
      :class="props.inputClassName"
      v-model="currentValue"
      :invalid="invalid"
      :disabled="readonly || disabled"
      v-bind="otherAttrs"
      @input="handleInput"
      @update:model-value="onUpdate"
      @blur="onBlur"
    />
    <slot></slot>
  </Field>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs } from "vue";
import InputNumber, {
  InputNumberEmitsOptions,
  InputNumberProps,
  InputNumberInputEvent,
} from "primevue/inputnumber";
import Field from "@/ui/Field.vue";
import type { FieldLayout } from "@/ui/Field.vue";
import { isString } from "@/util/guards";

export type Props = {
  modelValue?: any;
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
const otherAttrs: InputNumberProps = useAttrs();

const currentValue = ref(props.modelValue);

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
  },
);

const emit = defineEmits(["update:modelValue", "blur"]);

const handleInput = (event: InputNumberInputEvent) => {
  currentValue.value = isString(event.value) ? +event.value : event.value;
  emit("update:modelValue", currentValue.value);
};

const onUpdate: InputNumberEmitsOptions["update:modelValue"] = (newValue) => {
  emit("update:modelValue", newValue);
};

const onBlur: InputNumberEmitsOptions["blur"] = (newValue) => {
  emit("blur", newValue);
};
</script>
