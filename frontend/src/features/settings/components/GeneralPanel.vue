<template>
  <Panel header="Appearance" toggleable>
    <SwitchSettings />
    <NumberField
      label="Auto Measure Distance Delay in Milliseconds"
      v-model="store.settings.auto_measure_distance_delay_ms"
      inputId="auto_measure_distance_delay_ms"
      :min="50"
      :step="50"
      showButtons
    />
    <VideoSettings />
  </Panel>
  <Music collapsed toggleable header="Music" />
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";

import Music from "@/features/settings/components/Music.vue";
import SwitchSettings from "@/features/settings/components/SwitchSettings.vue";
import VideoSettings from "@/features/settings/components/VideoSettings.vue";
import Panel from "@/ui/Panel.vue";
import NumberField from "@/ui/NumberField.vue";

const store = useSettingsStore();
</script>

<style scoped lang="scss">
.field {
  label {
    display: block;
  }
}
</style>
