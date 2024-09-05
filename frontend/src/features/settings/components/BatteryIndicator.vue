<template>
  <div class="battery-indicator">
    <div class="typed">
      Battery:
      <span>{{ percentage }}%</span>
      <i class="pi pi-bolt"></i>
      <span>{{ batteryVoltage }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onUnmounted, onMounted } from "vue";

import { isNumber } from "@/util/guards";
import { useSettingsStore, useBatteryStore } from "@/features/settings/stores";

const POLL_SHORT_INTERVAL_MS = 60000; // 1 minute
const POLL_LONG_INTERVAL_MS = 60000 * 10; // 10 minutes

const batteryStore = useBatteryStore();
const settingsStore = useSettingsStore();
const intervalId = ref<NodeJS.Timeout>();

const batteryTotalVoltage = computed(
  () => settingsStore.settings.battery_full_voltage || 8.4,
);

const batteryVoltage = computed(() =>
  isNumber(batteryStore.voltage)
    ? `${batteryStore.voltage.toFixed(2)}V of ${batteryTotalVoltage.value.toFixed(2)}V`
    : batteryStore.voltage,
);

const percentage = computed(() =>
  ((batteryStore.voltage / batteryTotalVoltage.value) * 100).toFixed(2),
);

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
  const interval = getPollInterval(Number(percentage.value));
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
  display: inline-block;
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
</style>
