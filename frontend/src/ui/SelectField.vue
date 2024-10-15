<template>
  <div class="p-field" :class="props.fieldClassName">
    <span class="label" v-if="label" :class="labelClassName"
      >{{ label }}
      <span v-if="message" class="message">
        {{ message }}
      </span>
    </span>
    <Select
      :pt="{ input: { id: field, name: field } }"
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
.label {
  font-weight: bold;
  position: relative;
  display: flex;
  flex-direction: column;
  .message {
    background-color: transparent;
    color: var(--red-400);
  }
}
@import "./field.scss";
:deep(.p-select-dropdown) {
  width: 0.8rem;

  .p-icon {
    position: relative;
    width: 0.5rem;
    right: 50%;
  }
}

:deep(.p-select-label) {
  padding: 0.15rem 0.4rem;

  @media (min-width: 576px) {
    padding: 0.25rem 0.7rem;
  }

  @media (min-width: 768px) {
    padding: 0.3rem 0.7rem;
  }

  @media (min-width: 1200px) {
    padding: 0.4rem 0.7rem;
  }
}
</style>
