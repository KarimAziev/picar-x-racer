<template>
  <Fieldset toggleable legend="Surface Color">
    <ColorOptions
      title="Preset Colors"
      color-picker-id="surface-color"
      :reset-disabled="resetDisabled"
      v-model:color="store.surfaceColor"
      :options="surfaceOptions"
      @update:color="store.updateSurfaceColor"
      @reset:color="store.resetSurface"
    />
  </Fieldset>
</template>

<script setup lang="ts">
import Fieldset from "primevue/fieldset";
import { computed } from "vue";
import { useThemeStore } from "@/features/settings/stores";
import ColorOptions from "@/features/settings/components/theming/ColorOptions.vue";
import { surfaceOptions } from "@/presets/surfaces";

const store = useThemeStore();

const resetDisabled = computed(() => store.isSurfaceColorDefault);
</script>
