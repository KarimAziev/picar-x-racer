<template>
  <button
    type="button"
    class="inline-flex w-8 h-8 p-0 items-center justify-center surface-0 dark:surface-800 border border-surface-200 dark:border-surface-600 rounded"
    @click="handleToggleDarkTheme"
  >
    <i :class="`dark:text-white pi ${iconClass}`" />
  </button>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useThemeStore } from "@/features/settings/stores";
import {
  defaultDarkState,
  defaultLightState,
} from "@/features/settings/stores/theme";

const store = useThemeStore();

const iconClass = computed(() => (store.dark ? "pi-sun" : "pi-moon"));

const handleToggleDarkTheme = () => {
  store.toggleDarkTheme();

  if (!store.dark && store.surfaceColor === defaultDarkState.surfaceColor) {
    store.updateSurfaceColor(defaultLightState.surfaceColor);
  } else if (
    store.dark &&
    store.surfaceColor === defaultLightState.surfaceColor
  ) {
    store.updateSurfaceColor(defaultDarkState.surfaceColor);
  }
};
</script>
