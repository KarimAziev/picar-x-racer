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
import { ref, defineAsyncComponent, computed, onMounted } from "vue";
import Messager from "@/features/messager/Messager.vue";
import LazySettings from "@/features/settings/LazySettings.vue";
import { useSettingsStore } from "@/features/settings/stores";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import { onUnmounted } from "vue";

const isMobile = useDeviceWatcher();
const initialInnerHeight = ref(window.innerHeight);
const isFullscreen = ref();

const updateAppHeight = () => {
  const vh = window.innerHeight * 0.01;

  document.documentElement.style.setProperty("--app-height", `${vh * 100}px`);

  if (window.innerHeight !== initialInnerHeight.value) {
    isFullscreen.value = true;
    unlockScroll();
    lockScroll();
  } else {
    isFullscreen.value = false;
    unlockScroll();
  }
};

const resetInitialHeight = () => {
  initialInnerHeight.value = window.innerHeight;
  isFullscreen.value = false;
};

const lockScroll = () => {
  document.addEventListener("scroll", preventScroll, { passive: false });
  document.addEventListener("touchmove", preventScroll, { passive: false });
  document.addEventListener("wheel", preventScroll, { passive: false });
  document.body.style.position = "fixed";
};

const unlockScroll = () => {
  document.removeEventListener("scroll", preventScroll);
  document.removeEventListener("touchmove", preventScroll);
  document.removeEventListener("wheel", preventScroll);
  document.body.style.position = "";
};

const preventScroll = (e: Event) => {
  if (isFullscreen.value) {
    e.preventDefault();
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
  window.addEventListener("orientationchange", resetInitialHeight);
});

onUnmounted(() => {
  window.removeEventListener("resize", updateAppHeight);
  window.removeEventListener("orientationchange", resetInitialHeight);
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
