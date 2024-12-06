<template>
  <Field
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :label="label"
    :message="msg"
    :layout="layout"
  >
    <TextInput
      ref="inputRef"
      :invalid="!!msg"
      :id="field"
      :pt="{ input: { id: field } }"
      :class="inputClass"
      v-model="inputValue"
      @keyup.enter="handleKeyEnter"
      v-bind="omit(['modelValue'], { ...props, ...otherAttrs })"
      @blur="handleKeyEnter"
      @update:model-value="handleResetMsg"
    />
    <div class="flex flex-wrap labels gap-4">
      <Button
        class="chip"
        v-for="(val, i) in currentValue"
        :key="i"
        icon="pi pi-times"
        :label="val"
        severity="danger"
        outlined
        variant="text"
        @click="() => removeValue(val)"
      />
    </div>
  </Field>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs } from "vue";
import TextInput from "primevue/inputtext";
import type { InputTextProps } from "primevue/inputtext";
import Button from "primevue/button";
import Field from "@/ui/Field.vue";
import type { FieldLayout } from "@/ui/Field.vue";
import { omit } from "@/util/obj";

export interface Props {
  modelValue: string[] | null;
  label?: string;
  field?: string;
  fieldClassName?: string;
  labelClassName?: string;
  inputClass?: string;
  readonly?: boolean;
  disabled?: boolean;
  layout?: FieldLayout;
  size?: "small" | "large" | undefined;
}
const props = defineProps<Props>();
const otherAttrs: InputTextProps = useAttrs();

const currentValue = ref(props.modelValue);
const msg = ref<string | null>(null);

const inputValue = ref("");
const inputRef = ref<HTMLInputElement | null>(null);

const handleResetMsg = () => {
  msg.value = null;
};
watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
  },
);

const emit = defineEmits(["update:modelValue"]);

const handleKeyEnter = async () => {
  const newValue = inputValue.value;
  if (!newValue.length) {
    return;
  }
  if (currentValue.value?.includes(newValue)) {
    msg.value = "Already exists";
    return;
  }
  currentValue.value = !currentValue.value
    ? [newValue]
    : [...currentValue.value, newValue];

  inputValue.value = "";
  emit("update:modelValue", currentValue.value);
};

const removeValue = (removedValue: string) => {
  const nextValue =
    currentValue.value?.filter((val) => val !== removedValue) || null;
  currentValue.value = nextValue;
  emit("update:modelValue", currentValue.value);
};
</script>
<style scoped lang="scss">
.labels {
  max-width: 100px;
}
.chip {
  padding: 2px 4px;
  flex-direction: row-reverse;
  width: fit-content;
}
</style>
