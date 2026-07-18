<template>
  <Fieldset toggleable legend="Surface Color">
    <ColorOptions
      color-picker-id="surface-color"
      v-model:color="store.surfaceColor"
      :options="surfaceOptions"
      @update:color="handleUpdateSurfaceColor"
    >
      <Button
        size="small"
        :disabled="resetDisabled"
        label="Reset"
        @click="store.resetSurface"
      />
    </ColorOptions>
  </Fieldset>
</template>

<script setup lang="ts">
import Fieldset from "primevue/fieldset";
import { computed } from "vue";
import { useThemeStore } from "@/features/settings/stores";
import ColorOptions from "@/features/settings/components/theming/ColorOptions.vue";
import { surfaceOptions } from "@/presets/surfaces";

const store = useThemeStore();

const handleUpdateSurfaceColor = (newColor?: string) => {
  if (newColor) {
    store.updateSurfaceColor(newColor);
  }
};

const resetDisabled = computed(() => store.isSurfaceColorDefault);
</script>
