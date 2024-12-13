<template>
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
          label="Distance Measure Delay (ms)"
          v-model="store.data.auto_measure_distance_delay_ms"
          v-tooltip="
            'The time interval between successive auto distance measurements in milliseconds. This is applicable only when `auto_measure_distance_mode` is enabled. '
          "
          inputId="auto_measure_distance_delay_ms"
          :min="50"
          :step="50"
          showButtons
        />
        <NumberField
          label="Battery auto measure interval (seconds)"
          v-model="store.data.battery_auto_measure_seconds"
          inputId="battery_auto_measure_seconds"
          v-tooltip="
            'The interval in seconds between automatically measuring the ADC battery level'
          "
          :min="10"
          :step="10"
          showButtons
          :normalizeValue="roundNumber"
        />
        <NumberField
          label="Battery full voltage"
          v-tooltip="'The full voltage of the battery'"
          v-model="store.data.battery_full_voltage"
          inputId="battery_full_voltage"
          :min="7.0"
          :step="0.1"
          showButtons
          :normalizeValue="roundToOneDecimalPlace"
        />
        <NumberField
          label="The Maximum Speed"
          v-model="store.data.max_speed"
          v-tooltip="'The maximum allowed speed of the robot'"
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
import { roundToOneDecimalPlace, roundNumber } from "@/util/number";

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
