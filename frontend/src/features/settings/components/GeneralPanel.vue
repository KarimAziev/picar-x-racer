<template>
  <Panel collapsed header="System" toggleable>
    <div class="flex gap-10">
      <Restart />
      <Shutdown />
    </div>
  </Panel>
  <Panel header="Appearance" toggleable>
    <SwitchSettings>
      <FPSToggle v-tooltip="'Whether to draw FPS on the top-right corner'" />
    </SwitchSettings>
  </Panel>
  <Panel header="Camera/Robot" toggleable>
    <div class="wrapper">
      <div class="column">
        <VideoSettings />
      </div>

      <div class="column">
        <NumberField
          label="The Maximum Speed"
          v-model="store.data.robot.max_speed"
          v-tooltip="'The maximum allowed speed of the robot'"
          inputId="settings.data.max_speed"
          :min="10"
          :step="10"
          :max="100"
          showButtons
          @update:model-value="handleUpdateMaxSpeed"
        />
        <NumberField
          label="Distance Measure Delay (ms)"
          v-model="store.data.robot.auto_measure_distance_delay_ms"
          v-tooltip="
            'The time interval between successive auto distance measurements in milliseconds. This is applicable only when `auto_measure_distance_mode` is enabled. '
          "
          inputId="auto_measure_distance_delay_ms"
          :min="50"
          :step="50"
          showButtons
        />
        <ToggleSwitchField
          label="Auto-measure distance"
          v-tooltip="'Toggle auto-measuring with ultrasonic'"
          layout="row-reverse"
          :pt="{ input: { id: 'auto_measure_distance_mode' } }"
          v-model="store.data.robot.auto_measure_distance_mode"
          @update:model-value="handleToggleAutomeasureDistance"
        />
      </div>
    </div>
  </Panel>
  <Panel collapsed header="Battery" toggleable>
    <BatterySettings />
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

import BatterySettings from "@/features/settings/components/general/BatterySettings.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import Shutdown from "@/features/settings/components/system/Shutdown.vue";
import Restart from "@/features/settings/components/system/Restart.vue";

const store = useSettingsStore();
const controllerStore = useControllerStore();

const handleUpdateMaxSpeed = (value: number) => {
  if (controllerStore.model?.connected) {
    controllerStore.setMaxSpeed(value);
  }
};
const handleToggleAutomeasureDistance = (value: boolean) => {
  controllerStore.sendMessage({
    action: value ? "startAutoMeasureDistance" : "stopAutoMeasureDistance",
  });
};
</script>
<style scoped lang="scss">
@use "@/assets/scss/two-column-layout.scss";
</style>
