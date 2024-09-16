<template>
  <RouterView />
  <LazySettings />
  <Messager />
  <div class="indicators" v-if="!isMobile && isSettingsLoaded">
    <TextToSpeechButton />
    <MusicPlayer />
    <CalibrationModeInfo />
    <Distance />
    <BatteryIndicator />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from "vue-router";
import { defineAsyncComponent, computed } from "vue";
import Messager from "@/features/messager/Messager.vue";
import LazySettings from "@/features/settings/LazySettings.vue";
import { isMobileDevice } from "@/util/device";
import { useSettingsStore } from "@/features/settings/stores";

const isMobile = computed(() => isMobileDevice());
const settingsStore = useSettingsStore();
const isSettingsLoaded = computed(() => settingsStore.loaded);

const Distance = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Distance.vue"),
});

const TextToSpeechButton = defineAsyncComponent({
  loader: () => import("@/features/settings/components/TextToSpeechButton.vue"),
});

const MusicPlayer = defineAsyncComponent({
  loader: () => import("@/ui/MusicPlayer.vue"),
});

const BatteryIndicator = defineAsyncComponent({
  loader: () => import("@/features/settings/components/BatteryIndicator.vue"),
});
const CalibrationModeInfo = defineAsyncComponent({
  loader: () =>
    import("@/features/controller/components/CalibrationModeInfo.vue"),
});
</script>
<style scoped lang="scss">
.indicators {
  position: absolute;
  left: 0;
  bottom: 0;
  z-index: 11;
  text-align: left;
  user-select: none;
}
@media screen and (max-width: 1290px) {
  :global(body) {
    font-size: 0.7rem;
  }
  :deep(.p-datatable-table) {
    font-size: 0.85rem;
  }
}
@media screen and (max-width: 1200px) {
  :global(body) {
    font-size: 0.6rem;
  }
  :deep(.p-datatable-table) {
    font-size: 0.7rem;
  }
}
</style>
