<template>
  <ToggleableView setting="general.show_battery_indicator">
    <div class="flex max-w-[70vw] gap-2 overflow-x-auto items-center">
      <span v-if="batteryError" v-tooltip.left="batteryError">
        <i class="pi pi-exclamation-triangle color-error cursor-pointer" />
      </span>
      <i
        v-if="batteryLoading && !indicators.length"
        class="pi pi-spin pi-spinner"
      />
      <BatteryIndicator
        v-else
        v-for="(indicator, i) in indicators"
        :key="i"
        :name="indicator.config.name"
        :voltage="indicator.metrics?.voltage"
        :current="indicator.metrics?.current"
        :percentage="indicator.metrics?.percentage"
        :error="indicator.metrics?.error"
        :loading="batteryLoading"
        :class="severityClass(indicator.config, indicator.metrics)"
      />
    </div>
  </ToggleableView>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted } from "vue";
import { useBatteryStore, useRobotStore } from "@/features/settings/stores";
import type { Battery as BatteryConfig } from "@/features/settings/interface";
import type { BatteryResponse } from "@/features/settings/stores/battery";
import ToggleableView from "@/ui/ToggleableView.vue";

const batteryStore = useBatteryStore();
const robotStore = useRobotStore();

const BatteryIndicator = defineAsyncComponent({
  loader: () => import("@/ui/BatteryIndicator.vue"),
});

const batteryError = computed(() => batteryStore.error);

const batteryLoading = computed(() => batteryStore.loading);

const indicators = computed(() =>
  robotStore.data.batteries
    .filter((config) => config.enabled)
    .map((config) => ({
      config,
      metrics: batteryStore.batteries.find(
        (metrics) => metrics.name === config.name,
      ),
    })),
);

const severityClass = (config: BatteryConfig, metrics?: BatteryResponse) => {
  if (metrics?.error) {
    return "color-error";
  }
  if (metrics?.voltage === null || metrics?.voltage === undefined) {
    return;
  }
  if (metrics.voltage >= config.warn_voltage) {
    return "color-success";
  }
  if (metrics.voltage > config.danger_voltage) {
    return "color-warning";
  }
  return "color-error";
};

onMounted(batteryStore.fetchBatteryMetrics);
</script>
