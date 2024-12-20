<template>
  <Button
    v-if="fullscreenEnabled"
    @click="handleToggleFullscreen"
    :icon="iconName"
    aria-label="Toggle fullscreen mode"
    variant="text"
    size="small"
    rounded
    v-tooltip="tooltipText"
  ></Button>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useFullscreen } from "@/composables/useFullscreen";

const { fullscreenEnabled, isFullscreen, handleToggleFullscreen } =
  useFullscreen();

const iconName = computed(
  () =>
    `pi ${isFullscreen.value ? "pi-window-minimize" : "pi-window-maximize"}`,
);

const tooltipText = computed(() =>
  isFullscreen.value ? "Exit fullscreen" : "Enter fullscreen mode",
);
</script>
