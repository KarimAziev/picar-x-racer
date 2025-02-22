<template>
  <Fieldset toggleable legend="Primary Color">
    <ColorOptions
      color-picker-id="primary-color"
      :options="colorOptions"
      v-model:color="store.primaryColor"
      @update:color="store.updatePrimaryColor"
    >
      <Button
        size="small"
        :disabled="resetDisabled"
        label="Reset"
        @click="store.resetPrimaryColor"
      />
    </ColorOptions>
  </Fieldset>
</template>

<script setup lang="ts">
import Fieldset from "primevue/fieldset";
import { computed } from "vue";
import { useThemeStore } from "@/features/settings/stores";
import ColorOptions from "@/features/settings/components/theming/ColorOptions.vue";
import { colorOptions } from "@/features/settings/components/theming/colors";

const store = useThemeStore();

const resetDisabled = computed(() => store.isPrimaryColorDefault);
</script>
