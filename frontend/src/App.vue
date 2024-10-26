<template>
  <RouterView />
  <LazySettings />
  <Messager />
  <div class="indicators" v-if="!isMobile && isSettingsLoaded">
    <Recording />
    <CalibrationModeInfo />
    <TextToSpeechInput v-if="isTextToSpeechInputEnabled" />
    <MusicPlayer v-if="isPlayerEnabled" />
    <Distance />
    <BatteryIndicator />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from "vue-router";
import { defineAsyncComponent, computed, onMounted } from "vue";
import Messager from "@/features/messager/Messager.vue";
import LazySettings from "@/features/settings/LazySettings.vue";
import { useSettingsStore } from "@/features/settings/stores";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import { onUnmounted } from "vue";

const isMobile = useDeviceWatcher();
const updateAppHeight = () => {
  const vh = window.innerHeight * 0.01;

  document.documentElement.style.setProperty("--app-height", `${vh * 100}px`);

  if (window.innerHeight === screen.height) {
    document.body.style.overflow = "hidden";
    document.body.style.position = "fixed";
  } else {
    document.body.style.overflow = "";
    document.body.style.position = "";
  }
};
const settingsStore = useSettingsStore();
const isSettingsLoaded = computed(() => settingsStore.loaded);
const isTextToSpeechInputEnabled = computed(
  () => settingsStore.settings.text_to_speech_input,
);
const isPlayerEnabled = computed(() => settingsStore.settings.show_player);

const Distance = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Distance.vue"),
});

const TextToSpeechInput = defineAsyncComponent({
  loader: () => import("@/features/settings/components/TextToSpeechInput.vue"),
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
const Recording = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/VideoRecordingIndicator.vue"),
});

onMounted(() => {
  updateAppHeight();
  window.addEventListener("resize", updateAppHeight);
});

onUnmounted(() => {
  window.removeEventListener("resize", updateAppHeight);
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
</style>
