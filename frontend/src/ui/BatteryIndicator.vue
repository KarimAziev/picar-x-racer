<template>
  <div :class="className">
    <span class="bold">{{ batteryVoltage }}</span>
    <i class="pi pi-bolt"></i>
    <span class="bold">{{ percentageAdjusted }}%</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useSettingsStore, useBatteryStore } from "@/features/settings/stores";
import { roundNumber } from "@/util/number";

const batteryStore = useBatteryStore();
const settingsStore = useSettingsStore();

const batteryTotalVoltage = computed(
  () => settingsStore.data.battery.full_voltage,
);

const batteryVoltage = computed(() => `${batteryStore.voltage || 0}V`);

const batteryVoltageAdjusted = computed(() =>
  roundNumber(batteryStore.voltage - settingsStore.data.battery.min_voltage, 2),
);

const batteryTotalVoltageAdjusted = computed(() =>
  roundNumber(
    batteryTotalVoltage.value - settingsStore.data.battery.min_voltage,
    2,
  ),
);

const percentageAdjusted = computed(() =>
  roundNumber(
    Math.max(
      0,
      batteryVoltageAdjusted.value / batteryTotalVoltageAdjusted.value,
    ) * 100,
    1,
  ),
);

const className = computed(() => {
  const voltage = batteryStore.voltage;

  if (voltage >= settingsStore.data.battery.warn_voltage) {
    return "color-primary";
  } else if (
    voltage < settingsStore.data.battery.warn_voltage &&
    voltage > settingsStore.data.battery.danger_voltage
  ) {
    return "color-warning";
  } else {
    return "color-error blink";
  }
});
</script>
<style scoped lang="scss">
@use "@/assets/scss/blink";
</style>
