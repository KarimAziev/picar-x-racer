<template>
  <NumberField
    label="The Maximum Speed"
    v-model="store.data.robot.max_speed"
    tooltip="The maximum allowed speed of the robot"
    inputId="settings.data.max_speed"
    :min="10"
    :step="10"
    :max="100"
    showButtons
    @update:model-value="handleUpdateMaxSpeed"
  />
  <NumberInputField
    label="Ultrasonic measurement interval (ms)"
    v-model="store.data.robot.auto_measure_distance_delay_ms"
    tooltip="Time between ultrasonic readings while automatic measurement is enabled."
    inputId="auto_measure_distance_delay_ms"
    :min="1"
    :step="1"
    showButtons
  />
  <ToggleSwitchField
    label="Auto-measure ultrasonic distance"
    tooltip="Automatically read distance from the ultrasonic sensor."
    fieldClassName="flex-row-reverse gap-2.5 items-center justify-end mt-4"
    field="auto_measure_distance_mode"
    layout="row-reverse"
    v-model="store.data.robot.auto_measure_distance_mode"
    @update:model-value="handleToggleAutomeasureDistance"
  />
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import NumberField from "@/ui/NumberField.vue";
import { useControllerStore } from "@/features/controller/store";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import NumberInputField from "@/ui/NumberInputField.vue";

const store = useSettingsStore();
const controllerStore = useControllerStore();

const handleUpdateMaxSpeed = (value: number | null) => {
  if (value !== null && controllerStore.model?.connected) {
    controllerStore.setMaxSpeed(value);
  }
};
const handleToggleAutomeasureDistance = (value: boolean) => {
  controllerStore.sendMessage({
    action: value ? "startAutoMeasureDistance" : "stopAutoMeasureDistance",
  });
};
</script>
