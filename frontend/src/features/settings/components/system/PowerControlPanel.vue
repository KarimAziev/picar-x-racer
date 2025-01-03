<template>
  <div class="flex items-center justify-end gap-2" :class="className[0]">
    <slot></slot>
    <ToggleableView setting="general.show_battery_indicator">
      <BatteryIndicator
        :class="className[1]"
        :value="batteryVoltage"
        :percentage="percentage"
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

const batteryVoltage = computed(() => batteryStore.voltage);

const percentage = computed(() => batteryStore.percentage);

const className = computed(() => {
  const voltage = batteryStore.voltage;

  if (voltage >= settingsStore.data.battery.warn_voltage) {
    return ["color-success"];
  } else if (
    voltage < settingsStore.data.battery.warn_voltage &&
    voltage > settingsStore.data.battery.danger_voltage
  ) {
    return ["color-warning"];
  } else {
    return ["color-error"];
  }
});
</script>
