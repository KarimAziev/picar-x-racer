<template>
  <div class="battery-indicator">
    <div :class="className">
      Nominal battery:
      <span>{{ percentage }}%</span>
      <i class="pi pi-bolt"></i>
      <span>{{ batteryVoltage }}</span>
    </div>
    <div :class="className">
      Battery:
      <span>{{ percentageAdjusted }}%</span>
      <i class="pi pi-bolt"></i>
      <span
        >{{ batteryVoltageAdjusted.toFixed(2) }}V of
        {{ batteryTotalVoltageAdjusted.toFixed(2) }}V</span
      >
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";

import { isNumber } from "@/util/guards";
import { useSettingsStore, useBatteryStore } from "@/features/settings/stores";
import { roundNumber } from "@/util/number";

const BATTERY_TWO_LEDS_LEVEL = 7.6;
const BATTERY_ONE_LEDS_LEVEL = 7.15;
const BATTERY_DANGER_LEVEL = 6.5;
const BATTERY_MIN_LEVEL = 6.0;

const batteryStore = useBatteryStore();
const settingsStore = useSettingsStore();

const batteryTotalVoltage = computed(
  () => settingsStore.data.battery_full_voltage || 8.4,
);

const batteryTotalVoltageAdjusted = computed(() =>
  roundNumber(batteryTotalVoltage.value - BATTERY_MIN_LEVEL, 2),
);

const batteryVoltage = computed(() =>
  isNumber(batteryStore.voltage)
    ? `${batteryStore.voltage.toFixed(2)} of ${batteryTotalVoltage.value.toFixed(2)}V`
    : batteryStore.voltage,
);

const batteryVoltageAdjusted = computed(() =>
  roundNumber(
    isNumber(batteryStore.voltage)
      ? Math.max(0, batteryStore.voltage - BATTERY_MIN_LEVEL)
      : batteryStore.voltage,
    2,
  ),
);

const percentage = computed(() =>
  ((batteryStore.voltage / batteryTotalVoltage.value) * 100).toFixed(2),
);

const percentageAdjusted = computed(() =>
  (
    Math.max(
      0,
      batteryVoltageAdjusted.value / batteryTotalVoltageAdjusted.value,
    ) * 100
  ).toFixed(2),
);

const className = computed(() => {
  const voltage = batteryStore.voltage;

  if (voltage >= BATTERY_TWO_LEDS_LEVEL) {
    return "two-led";
  } else if (voltage >= BATTERY_ONE_LEDS_LEVEL) {
    return "one-led";
  } else if (
    voltage < BATTERY_ONE_LEDS_LEVEL &&
    voltage > BATTERY_DANGER_LEVEL
  ) {
    return "warning";
  } else {
    return "danger";
  }
});

onMounted(batteryStore.fetchBatteryStatus);
</script>

<style scoped lang="scss">
@import "@/assets/animation.scss";
.typed {
  overflow: hidden;
  white-space: nowrap;
  animation:
    typing 2s steps(30, end),
    blink-caret 2s steps(1, end) reverse;
  border-right: 3px solid transparent;
}
.typed::after {
  content: "";
  display: inline-block;
  width: 0;
  overflow: hidden;
  animation: hide-caret 0s steps(30, end) forwards 2s;
}
.two-led {
  color: var(--robo-color-primary);
}
.one-led {
  color: var(--robo-color-secondary);
}
.warning {
  color: var(--color-warn);
}
.danger {
  color: var(--color-error);
}
</style>
