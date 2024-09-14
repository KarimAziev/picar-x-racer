<template>
  <div class="p-field" :class="props.fieldClassName">
    <LabelBox
      :label="label"
      :class="labelClassName"
      :for="field"
      :message="message"
    />
    <Select
      :id="props.field"
      :options="options"
      :optionLabel="optionLabel"
      :optionValue="optionValue"
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
import { ref, watch, useAttrs, computed } from "vue";
import type { SelectEmitsOptions, SelectProps } from "primevue/select";
import { InlineMessageProps } from "primevue/inlinemessage";
import Select from "primevue/select";
import LabelBox from "@/ui/LabelBox.vue";

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
  simpleOptions?: boolean;
  options: SelectProps["options"];
  optionLabel?: string;
  optionValue?: string;
  readonly?: boolean;
  disabled?: boolean;
};
const props = defineProps<Props>();
const otherAttrs = useAttrs();

const currentValue = ref(props.modelValue);

const optionLabel = computed(() =>
  props.simpleOptions ? undefined : props.optionLabel || "label",
);
const optionValue = computed(() =>
  props.simpleOptions ? undefined : props.optionValue || "value",
);

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
<style scoped lang="scss">
@import "./field.scss";
</style>
