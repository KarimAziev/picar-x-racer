<template>
  <ToggleSwitchField
    tooltipHelp="'Whether to use dark theme'"
    label="Dark Theme"
    layout="row-reverse"
    fieldClassName="flex-row-reverse gap-2.5 items-center justify-end"
    field="dark-theme-switch"
    v-model="store.dark"
    @update:model-value="handleToggleDarkTheme"
  />
</template>

<script setup lang="ts">
import { useThemeStore } from "@/features/settings/stores";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import {
  defaultDarkState,
  defaultLightState,
} from "@/features/settings/stores/theme";

const store = useThemeStore();

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
