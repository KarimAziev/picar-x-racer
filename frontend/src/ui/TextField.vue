<template>
  <Field
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :label="label"
    :message="message"
    :layout="layout"
  >
    <InputText
      v-tooltip="tooltip"
      :inputId="field"
      :pt="{ pcInput: { id: field } }"
      :class="props.inputClassName"
      v-model="currentValue"
      :invalid="invalid"
      :disabled="readonly || disabled"
      v-bind="otherAttrs"
      @update:model-value="onUpdate"
      @value-change="onChange"
    />
    <slot></slot>
  </Field>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs } from "vue";
import InputText, {
  InputTextEmitsOptions,
  InputTextProps,
} from "primevue/inputtext";
import Field from "@/ui/Field.vue";
import type { FieldLayout } from "@/ui/Field.vue";

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
const otherAttrs: InputTextProps = useAttrs();

const currentValue = ref(props.modelValue);

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
  },
);

const emit = defineEmits(["update:modelValue", "value-change"]);

const onUpdate: InputTextEmitsOptions["update:modelValue"] = (newValue) => {
  emit("update:modelValue", newValue);
};

const onChange: InputTextEmitsOptions["value-change"] = (newValue) => {
  emit("value-change", newValue);
};
</script>
