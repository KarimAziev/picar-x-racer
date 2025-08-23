<template>
  <ToggleableView setting="general.show_battery_indicator">
    <span v-if="batteryError" v-tooltip.left="batteryError">
      <i class="pi pi-exclamation-triangle color-error cursor-pointer" />
    </span>
    <BatteryIndicator
      :value="batteryVoltage"
      :percentage="percentage"
      :loading="batteryLoading"
    />
  </ToggleableView>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted } from "vue";
import { useBatteryStore } from "@/features/settings/stores";
import ToggleableView from "@/ui/ToggleableView.vue";

const batteryStore = useBatteryStore();

const BatteryIndicator = defineAsyncComponent({
  loader: () => import("@/ui/BatteryIndicator.vue"),
});

const batteryVoltage = computed<number>((previous) => {
  const value = batteryStore.voltage;
  return value !== undefined && value !== null ? value : previous || 0;
});

const batteryError = computed(() => batteryStore.error);

const batteryLoading = computed(() => batteryStore.loading);

const percentage = computed<number>((previous) => {
  const value = batteryStore.percentage;
  return value !== undefined && value !== null ? value : previous || 0;
});

onMounted(batteryStore.fetchBatteryStatus);
</script>
