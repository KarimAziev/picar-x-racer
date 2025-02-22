<template>
  <div class="flex flex-col gap-2 items-start px-1">
    <div v-if="title" class="text-sm font-medium">
      {{ title }}
    </div>
    <div class="inline-flex flex-col justify-start items-start gap-2 flex-wrap">
      <div
        class="self-stretch justify-start items-start gap-2 inline-flex flex-wrap"
      >
        <span class="text-sm font-medium">Preset: </span>
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
    <div class="flex gap-4 items-center flex-wrap">
      <Field
        label="Custom:"
        label-class-name="text-sm font-medium"
        layout="row"
      >
        <ColorPicker
          :inputId="colorPickerId"
          v-model:model-value="colorPickerValue"
          @update:model-value="handleUpdateColorPickerValue"
        />
      </Field>
      <template v-if="$slots.extra">
        <slot name="extra" />
      </template>
    </div>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { startCase, ensurePrefix } from "@/util/str";
import { ValueLabelOption } from "@/types/common";
import Field from "@/ui/Field.vue";

export interface ColorOption extends ValueLabelOption {
  color?: string;
}

const props = defineProps<{
  colorPickerId: string;
  options: ColorOption[];
  title?: string;
}>();

const color = defineModel<string>("color");
const emit = defineEmits(["update:color"]);

const findColorPickerValue = () => {
  const matchedOption = props.options.find(
    (opt) =>
      opt.color && (opt.color === color.value || opt.value === color.value),
  );
  return matchedOption?.color || color.value;
};

const colorPickerValue = ref(findColorPickerValue());

const handleUpdateColorPickerValue = (newColor: string) => {
  emit("update:color", ensurePrefix("#", newColor));
};

const handleUpdateColor = (newColor: string) => {
  emit("update:color", newColor);
};

watch(
  () => color.value,
  () => {
    const nextVal = findColorPickerValue();

    colorPickerValue.value = nextVal?.startsWith("#")
      ? nextVal.substring(1)
      : nextVal;
  },
);
</script>
