<template>
  <div class="flex items-center justify-end gap-2" :class="className">
    <slot></slot>
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
    <ToggleableView setting="general.show_shutdown_reboot_button">
      <ShutdownPopover />
    </ToggleableView>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import { useSettingsStore, useBatteryStore } from "@/features/settings/stores";
import ToggleableView from "@/ui/ToggleableView.vue";

const batteryStore = useBatteryStore();
const settingsStore = useSettingsStore();

const BatteryIndicator = defineAsyncComponent({
  loader: () => import("@/ui/BatteryIndicator.vue"),
});

const ShutdownPopover = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/system/ShutdownPopover.vue"),
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

const className = computed((previous) => {
  const voltage = batteryStore.voltage;

  if (batteryStore.loading || voltage === null || voltage === undefined) {
    return previous;
  }

  if (batteryStore.error) {
    return "color-error";
  }

  if (voltage >= settingsStore.data.battery.warn_voltage) {
    return "color-success";
  } else if (
    voltage < settingsStore.data.battery.warn_voltage &&
    voltage > settingsStore.data.battery.danger_voltage
  ) {
    return "color-warning";
  } else {
    return "color-error";
  }
});
</script>
