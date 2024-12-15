<template>
  <div :class="className">
    <span class="bold">{{ batteryVoltage }}</span>
    <i class="pi pi-bolt"></i>
    <span class="bold">{{ percentageAdjusted }}%</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { isNumber } from "@/util/guards";
import { useSettingsStore, useBatteryStore } from "@/features/settings/stores";
import { roundNumber } from "@/util/number";

const BATTERY_ONE_LEDS_LEVEL = 7.15;
const BATTERY_DANGER_LEVEL = 6.5;
const BATTERY_MIN_LEVEL = 6.0;

const batteryStore = useBatteryStore();
const settingsStore = useSettingsStore();

const batteryTotalVoltage = computed(
  () => settingsStore.data.battery_full_voltage,
);

const batteryTotalVoltageAdjusted = computed(() =>
  roundNumber(batteryTotalVoltage.value - BATTERY_MIN_LEVEL),
);

const batteryVoltage = computed(() => `${batteryStore.voltage || 0}V`);

const batteryVoltageAdjusted = computed(() =>
  roundNumber(
    isNumber(batteryStore.voltage)
      ? Math.max(0, batteryStore.voltage - BATTERY_MIN_LEVEL)
      : batteryStore.voltage,
    2,
  ),
);

const percentageAdjusted = computed(() =>
  (
    Math.max(
      0,
      batteryVoltageAdjusted.value / batteryTotalVoltageAdjusted.value,
    ) * 100
  ).toFixed(),
);

const className = computed(() => {
  const voltage = batteryStore.voltage;

  if (voltage >= BATTERY_ONE_LEDS_LEVEL) {
    return "color-primary";
  } else if (
    voltage < BATTERY_ONE_LEDS_LEVEL &&
    voltage > BATTERY_DANGER_LEVEL
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
