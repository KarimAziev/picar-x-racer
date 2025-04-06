<template>
  <ColorOptions
    :title="title"
    :color-picker-id="colorPickerId"
    v-model:color="color"
    :options="colorOptions"
    @update:color="handleUpdateColor"
  >
    <template #extra>
      <div>
        <span class="text-sm font-medium">Width: </span>
        <Slider
          class="w-32"
          :min="1"
          :max="100"
          v-model="size"
          @update:model-value="handleUpdateSize"
        />
      </div>
    </template>
    <div class="flex items-center gap-4">
      <Button
        label="Reset"
        size="small"
        :disabled="resetDisabled"
        @click="handleReset"
      />
      <div class="flex items-center gap-4" v-if="showFiberSettings">
        <div class="font-medium">
          Render Skeleton Fibers
          <TooltipHelp
            tooltip="When enabled, the setting overlays additional curved lines along the primary skeleton connections. These extra fibers simulate muscle, adding depth and a more three-dimensional feel to the detected pose."
          />
        </div>
        <Checkbox
          v-model="renderFiber"
          binary
          @update:model-value="handleUpdateFiber"
        />
      </div>
    </div>
  </ColorOptions>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { colorOptions } from "@/features/settings/components/theming/colors";
import ColorOptions from "@/features/settings/components/theming/ColorOptions.vue";
import TooltipHelp from "@/ui/TooltipHelp.vue";

const color = defineModel<string>("color");
const size = defineModel<number>("size");
const renderFiber = defineModel<boolean>("renderFiber");

const props = defineProps<{
  initialFiber?: boolean;
  initialSize?: number;
  initialColor?: string;
  colorPickerId: string;
  title?: string;
  showFiberSettings?: boolean;
  isResetDisabled?: boolean;
}>();

const emit = defineEmits([
  "update:color",
  "update:size",
  "update:renderFiber",
  "reset",
]);

const resetDisabled = computed(
  () =>
    props.isResetDisabled ||
    (props.initialColor === color.value &&
      props.initialSize === size.value &&
      props.initialFiber === renderFiber.value),
);

const handleUpdateColor = (newColor: string) => {
  emit("update:color", newColor);
};

const handleUpdateSize = (newColor: number | number[]) => {
  emit("update:size", newColor as number);
};

const handleUpdateFiber = (newColor: string) => {
  emit("update:renderFiber", newColor);
};

const handleReset = () => {
  color.value = props.initialColor;
  size.value = props.initialSize;
  if (props.showFiberSettings) {
    renderFiber.value = props.initialFiber;
  }

  emit("reset");
};
</script>
