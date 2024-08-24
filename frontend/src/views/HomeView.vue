<template>
  <PreloadMask :loading="true"> </PreloadMask>
  <SettingsPopup v-if="storeSettings.loaded" />
  <CarController />
  <BatteryIndicator v-if="storeSettings.loaded" />
</template>

<script setup lang="ts">
import { onMounted, computed, defineAsyncComponent } from "vue";
import { useSettingsStore } from "@/features/settings/stores";
import BatteryIndicator from "@/features/settings/components/BatteryIndicator.vue";
import PreloadMask from "@/ui/PreloadMask.vue";

const SettingsPopup = defineAsyncComponent({
  loader: () => import("@/features/settings/SettingsPopup.vue"),
});

const CarController = defineAsyncComponent({
  loader: () => import("@/features/controller/CarController.vue"),
});

const storeSettings = useSettingsStore();
const loaded = computed(() => storeSettings.loaded);

onMounted(() => {
  if (!loaded.value) {
    storeSettings.fetchSettingsInitial();
  }
});
</script>
<style scoped lang="scss"></style>
