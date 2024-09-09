<template>
  <div class="battery-indicator">
    <div class="typed">
      Nominal battery:
      <span>{{ percentage }}%</span>
      <i class="pi pi-bolt"></i>
      <span>{{ batteryVoltage }}</span>
    </div>
    <div :class="className">
      Battery:
      <span>{{ percentageAdjusted }} %</span>
      <i class="pi pi-bolt"></i>
      <span
        >{{ batteryVoltageAdjusted.toFixed(2) }}V of
        {{ batteryTotalVoltageAdjusted.toFixed(2) }}V</span
      >
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onUnmounted, onMounted } from "vue";

import { isNumber } from "@/util/guards";
import { useSettingsStore, useBatteryStore } from "@/features/settings/stores";

const BATTERY_DANGER_LEVEL = 6.7;
const BATTERY_GOOD_LEVEL = 7.8;

const POLL_SHORT_INTERVAL_MS = 60000; // 1 minute
const POLL_LONG_INTERVAL_MS = 60000 * 10; // 10 minutes

const batteryStore = useBatteryStore();
const settingsStore = useSettingsStore();
const intervalId = ref<NodeJS.Timeout>();

const batteryTotalVoltage = computed(
  () => settingsStore.settings.battery_full_voltage || 8.4,
);

const batteryTotalVoltageAdjusted = computed(
  () => batteryTotalVoltage.value - BATTERY_DANGER_LEVEL,
);

const batteryVoltage = computed(() =>
  isNumber(batteryStore.voltage)
    ? `${batteryStore.voltage.toFixed(2)}V of ${batteryTotalVoltage.value.toFixed(2)}V`
    : batteryStore.voltage,
);

const batteryVoltageAdjusted = computed(() =>
  isNumber(batteryStore.voltage)
    ? Math.max(0, batteryStore.voltage - BATTERY_DANGER_LEVEL)
    : batteryStore.voltage,
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

  if (voltage > BATTERY_GOOD_LEVEL) {
    return "typed";
  } else if (voltage > BATTERY_DANGER_LEVEL && voltage <= BATTERY_GOOD_LEVEL) {
    return "warning";
  } else {
    return "danger";
  }
});

const getPollInterval = (batteryPercentage: number) => {
  // Poll more frequently if battery is below 20%
  if (batteryPercentage < 20) {
    return POLL_SHORT_INTERVAL_MS;
  } else {
    // Poll less frequently otherwise
    return POLL_LONG_INTERVAL_MS;
  }
};

const fetchAndScheduleNext = async () => {
  await batteryStore.fetchBatteryStatus();
  const interval = getPollInterval(Number(percentageAdjusted.value));
  if (intervalId.value) clearInterval(intervalId.value);
  intervalId.value = setInterval(fetchAndScheduleNext, interval);
};

onMounted(async () => {
  await fetchAndScheduleNext();
});

onUnmounted(() => {
  if (intervalId.value) {
    clearInterval(intervalId.value);
  }
});
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
.warning {
  color: #ffcc00;
}
.danger {
  color: red;
}
</style>
