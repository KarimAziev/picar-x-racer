<template>
  <ColorOptions
    :title="title"
    color-picker-id="detection-bbox-color"
    v-model:color="store.bboxesColor"
    :options="colorOptions"
    @update:color="store.updateBBoxesColor"
  >
    <Button
      size="small"
      label="Reset"
      :disabled="isResetDisabled"
      @click="
        () => {
          store.bboxesColor = undefined;
        }
      "
    />
  </ColorOptions>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { colorOptions } from "@/features/settings/components/theming/colors";
import { useThemeStore } from "@/features/settings/stores";
import ColorOptions from "@/features/settings/components/theming/ColorOptions.vue";
import { defaultState } from "@/features/settings/stores/theme";

const store = useThemeStore();

defineProps<{ class?: string; title?: string }>();

const isResetDisabled = computed(
  () =>
    store.bboxesColor === defaultState.bboxesColor ||
    store.bboxesColor === store.primaryColor,
);
</script>
