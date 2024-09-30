<template>
  <div class="p-field" :class="props.fieldClassName">
    <span class="label" v-if="label" :class="labelClassName" :for="field"
      >{{ label }}
      <span v-if="message" class="message">
        {{ message }}
      </span>
    </span>
    <InputNumber
      showButtons
      :inputId="field"
      :pt="{ pcInput: { id: field } }"
      :class="props.inputClassName"
      v-model="currentValue"
      :invalid="invalid"
      :disabled="readonly || disabled"
      v-bind="otherAttrs"
      @update:model-value="onUpdate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs } from "vue";
import { InlineMessageProps } from "primevue/inlinemessage";
import InputNumber, {
  InputNumberEmitsOptions,
  InputNumberProps,
} from "primevue/inputnumber";

export type Props = {
  modelValue?: any;
  invalid?: boolean;
  message?: string;
  messageSeverity?: InlineMessageProps["severity"];
  label?: string;
  field?: string;
  fieldClassName?: string;
  labelClassName?: string;
  inputClassName?: string;
  readonly?: boolean;
  disabled?: boolean;
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

const emit = defineEmits(["update:modelValue"]);

const onUpdate: InputNumberEmitsOptions["update:modelValue"] = (newValue) => {
  emit("update:modelValue", newValue);
};
</script>
<style scoped lang="scss">
@import "./field.scss";
.label {
  display: block;
  font-weight: bold;
}
</style>
