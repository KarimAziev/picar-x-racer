<template>
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
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import NumberField from "@/ui/NumberField.vue";
import { useControllerStore } from "@/features/controller/store";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";

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
