<template>
  <Field
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :label="label"
    :message="message"
    :loading="loading"
  >
    <Select
      :pt="{ input: { id: field, name: field } }"
      :options="options"
      :optionLabel="optionLabel"
      :optionValue="optionValue"
      filter
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
import { ref, watch, useAttrs, computed } from "vue";
import type { SelectEmitsOptions, SelectProps } from "primevue/select";

import Select from "primevue/select";
import Field from "@/ui/Field.vue";

export type Props = {
  modelValue?: any;
  invalid?: boolean;
  message?: string;
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
  loading?: boolean;
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
