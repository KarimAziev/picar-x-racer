<template>
  <div class="flex items-center justify-end gap-2" :class="className">
    <slot></slot>
    <i v-if="isSettingsLoaded" class="pi pi-spin pi-spinner"></i>
    <Battery v-else-if="isBatteryEnabled" />
    <ToggleableView setting="general.show_shutdown_reboot_button">
      <ShutdownPopover />
    </ToggleableView>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import {
  useBatteryStore,
  useRobotStore,
  useSettingsStore,
} from "@/features/settings/stores";
import ToggleableView from "@/ui/ToggleableView.vue";

const batteryStore = useBatteryStore();
const robotStore = useRobotStore();
const settingsStore = useSettingsStore();

const isSettingsLoaded = computed(
  () => !robotStore.loaded || !settingsStore.loaded,
);

const isBatteryEnabled = computed(
  () =>
    robotStore.data.battery.enabled &&
    settingsStore.data.general.show_battery_indicator &&
    !isSettingsLoaded.value,
);

const Battery = defineAsyncComponent({
  loader: () => import("@/features/settings/components/system/Battery.vue"),
});

const ShutdownPopover = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/system/ShutdownPopover.vue"),
});

const className = computed((previous) => {
  const voltage = batteryStore.voltage;

  if (batteryStore.loading || voltage === null || voltage === undefined) {
    return previous;
  }

  if (batteryStore.error) {
    return "color-error";
  }

  if (voltage >= robotStore.data.battery.warn_voltage) {
    return "color-success";
  } else if (
    voltage < robotStore.data.battery.warn_voltage &&
    voltage > robotStore.data.battery.danger_voltage
  ) {
    return "color-warning";
  } else {
    return "color-error";
  }
});
</script>
