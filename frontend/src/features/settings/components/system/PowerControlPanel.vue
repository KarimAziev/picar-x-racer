<template>
  <div class="flex items-center justify-end gap-2">
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
import { useRobotStore, useSettingsStore } from "@/features/settings/stores";
import ToggleableView from "@/ui/ToggleableView.vue";

const robotStore = useRobotStore();
const settingsStore = useSettingsStore();

const isSettingsLoaded = computed(
  () => !robotStore.loaded || !settingsStore.loaded,
);

const isBatteryEnabled = computed(
  () =>
    robotStore.data.batteries.some((battery) => battery.enabled) &&
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
</script>
