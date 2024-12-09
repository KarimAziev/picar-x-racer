<template>
  <Panel header="Appearance" toggleable>
    <SwitchSettings>
      <FPSToggle />
    </SwitchSettings>
  </Panel>
  <Panel header="Camera/Robot" toggleable>
    <div class="wrapper">
      <div class="column">
        <VideoSettings />
      </div>

      <div class="column">
        <NumberField
          label="Auto Measure Delay (ms)"
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
        <slot></slot>
      </div>
    </div>
  </Panel>
  <Panel collapsed header="Music" toggleable>
    <Music />
  </Panel>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import Music from "@/features/settings/components/general/Music.vue";
import SwitchSettings from "@/features/settings/components/general/SwitchSettings.vue";
import VideoSettings from "@/features/settings/components/camera/VideoSettings.vue";
import Panel from "@/ui/Panel.vue";
import NumberField from "@/ui/NumberField.vue";
import FPSToggle from "@/features/settings/components/camera/FPSToggle.vue";
import { useControllerStore } from "@/features/controller/store";

const store = useSettingsStore();
const controllerStore = useControllerStore();

const handleUpdateMaxSpeed = (value: number) => {
  if (controllerStore.model?.connected) {
    controllerStore.setMaxSpeed(value);
  }
};
</script>
<style scoped lang="scss">
@use "@/assets/scss/two-column-layout.scss";
</style>
