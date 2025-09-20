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
    <TextInput
      ref="inputRef"
      :invalid="!!msg"
      :id="field"
      :pt="{ input: { id: field } }"
      @focus="handleFocus"
      :class="inputClass"
      :placeholder="placeholder"
      v-model="inputValue"
      @keyup.enter="handleKeyEnter"
      v-bind="omit(['modelValue'], { ...props, ...otherAttrs })"
      @blur="handleKeyEnter"
      @update:model-value="handleResetMsg"
      v-tooltip="tooltip"
    />
  </Field>
  <Popover
    ref="popoverRef"
    @show="handleSelectBeforeShow"
    @hide="handleSelectBeforeHide"
  >
    <div class="flex flex-col w-[120px] gap-x-1">
      <button
        class="inline-flex p-0 items-center justify-between"
        v-for="(val, i) in currentValue"
        :key="i"
        @click="() => removeValue(val)"
      >
        {{ val }}
        <span class="text-red-400 cursor-pointer">&times;</span>
      </button>
    </div>
  </Popover>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs, computed } from "vue";
import TextInput from "primevue/inputtext";
import type { InputTextProps } from "primevue/inputtext";
import type { PopoverMethods } from "primevue/popover";
import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";
import { omit } from "@/util/obj";
import { usePopupStore } from "@/features/settings/stores";

export interface Props extends FieldProps {
  modelValue: string[] | null;
  label?: string;
  field?: string;
  inputClass?: string;
  readonly?: boolean;
  disabled?: boolean;
  size?: "small" | "large" | undefined;
  tooltip?: string;
}

const popoverRef = ref<PopoverMethods>();
const props = defineProps<Props>();
const otherAttrs: InputTextProps = useAttrs();
const placeholder = computed(() =>
  currentValue.value && currentValue.value.length > 0
    ? `${currentValue.value.length} label${currentValue.value.length === 1 ? "" : "s"}`
    : "No labels",
);

const currentValue = ref(props.modelValue);
const msg = ref<string | null>(null);

const handleFocus = (ev: Event) => {
  if (
    popoverRef?.value &&
    currentValue.value &&
    currentValue.value.length > 0
  ) {
    popoverRef?.value?.show(ev);
  }
};

const inputValue = ref("");
const inputRef = ref<HTMLInputElement | null>(null);
const popupStore = usePopupStore();
const handleSelectBeforeShow = () => {
  popupStore.isEscapable = false;
};

const handleSelectBeforeHide = () => {
  popupStore.isEscapable = true;
};

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

const handleKeyEnter = async (ev: Event) => {
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
  if (currentValue.value && currentValue.value.length > 0) {
    popoverRef.value?.show(ev);
  }
  emit("update:modelValue", currentValue.value);
};

const removeValue = (removedValue: string) => {
  const nextValue =
    currentValue.value?.filter((val) => val !== removedValue) || null;
  currentValue.value = nextValue;
  if (!currentValue.value || !currentValue.value.length) {
    popoverRef.value?.hide();
  }
  emit("update:modelValue", currentValue.value);
};
</script>
