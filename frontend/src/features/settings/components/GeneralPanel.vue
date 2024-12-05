<template>
  <Panel header="Appearance" toggleable>
    <SwitchSettings />
    <NumberField
      label="Auto Measure Distance Delay in Milliseconds"
      v-model="store.data.auto_measure_distance_delay_ms"
      inputId="auto_measure_distance_delay_ms"
      :min="50"
      :step="50"
      showButtons
    />
    <NumberField
      label="The Maximum Speed"
      v-model="store.data.max_speed"
      inputId="settings.data.max_speed"
      :min="10"
      :step="10"
      :max="100"
      showButtons
      @update:model-value="handleUpdateMaxSpeed"
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
import { useControllerStore } from "@/features/controller/store";

const store = useSettingsStore();
const controllerStore = useControllerStore();

const handleUpdateMaxSpeed = (value: number) => {
  if (controllerStore.model?.connected) {
    controllerStore.setMaxSpeed(value);
  }
};
</script>
