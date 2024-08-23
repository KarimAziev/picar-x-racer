<template>
  <PreloadMask :loading="!loaded">
    <SettingsPopup />
    <CarController />
    <BatteryIndicator />
    <Messager />
  </PreloadMask>
</template>

<script setup lang="ts">
import { onMounted, computed, defineAsyncComponent } from "vue";
import { useSettingsStore } from "@/features/settings/stores";
import BatteryIndicator from "@/features/settings/components/BatteryIndicator.vue";
import Messager from "@/features/messager/Messager.vue";
import PreloadMask from "@/ui/PreloadMask.vue";

const SettingsPopup = defineAsyncComponent({
  loader: () => import("@/features/settings/SettingsPopup.vue"),
});

const CarController = defineAsyncComponent({
  loader: () => import("@/features/controller/CarController.vue"),
});

const settings = useSettingsStore();
const loaded = computed(() => settings.loaded);

onMounted(() => {
  if (!loaded.value) {
    settings.fetchSettings();
  }
});
</script>
<style scoped lang="scss"></style>
