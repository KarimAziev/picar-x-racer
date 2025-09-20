<template>
  <Field
    :message="message"
    :label="label"
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
    :messageClass="messageClass"
  >
    <InputText
      v-tooltip="tooltip"
      :inputId="field"
      :id="field"
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
import type { Props as FieldProps } from "@/ui/Field.vue";

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
