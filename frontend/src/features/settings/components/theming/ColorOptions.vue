<template>
  <div class="flex flex-col gap-2 items-start px-1">
    <div class="inline-flex flex-col justify-start items-start gap-2">
      <span class="text-sm font-medium">{{ title }}</span>
      <div
        class="self-stretch justify-start items-start gap-2 inline-flex flex-wrap"
      >
        <button
          v-for="colorOption of options"
          :key="colorOption.label"
          type="button"
          :title="startCase(colorOption.label)"
          @click="handleUpdateColor(colorOption.value)"
          class="outline outline-2 outline-offset-2 outline-transparent cursor-pointer p-0 rounded-[50%] w-5 h-5 focus:ring"
          :style="{
            backgroundColor: `${colorOption.color || colorOption.value}`,
            outlineColor: `${
              color === colorOption.value ? 'var(--p-primary-color)' : ''
            }`,
          }"
        ></button>
      </div>
    </div>
    <Field label="Custom:" label-class-name="text-sm font-medium">
      <ColorPicker
        :inputId="colorPickerId"
        v-model="colorPickerValue"
        @update:model-value="handleUpdateColor"
      />
    </Field>
    <Button
      size="small"
      :disabled="resetDisabled"
      label="Reset"
      @click="handleReset"
    />
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { startCase } from "@/util/str";
import { ValueLabelOption } from "@/types/common";
import Field from "@/ui/Field.vue";

export interface ColorOption extends ValueLabelOption {
  color?: string;
}

const props = defineProps<{
  colorPickerId: string;
  resetDisabled?: boolean;
  title?: string;
  options: ColorOption[];
}>();

const color = defineModel<string>("color", { required: true });
const emit = defineEmits(["update:color", "reset:color"]);

const findColorPickerValue = () => {
  const matchedOption = props.options.find(
    (opt) =>
      opt.color && (opt.color === color.value || opt.value === color.value),
  );
  return matchedOption?.color || color.value;
};

const colorPickerValue = ref(findColorPickerValue());

const handleUpdateColor = (newColor: string) => {
  emit("update:color", newColor);
};

const handleReset = () => {
  emit("reset:color");
};

watch(
  () => color.value,
  () => {
    colorPickerValue.value = findColorPickerValue();
  },
);
</script>
