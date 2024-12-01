<template>
  <RouterView />
  <LazySettings />
  <Messager v-if="!isMobile" />
  <div class="indicators" v-if="!isMobile && isSettingsLoaded">
    <Recording />
    <ToggleableView
      setting="show_object_detection_settings"
      v-if="!isPopupOpen"
    >
      <ObjectDetectionSwitch />
    </ToggleableView>
    <CalibrationModeInfo />
    <ToggleableView setting="text_to_speech_input">
      <TextToSpeechInput />
    </ToggleableView>
    <ToggleableView setting="show_player">
      <MusicPlayer />
    </ToggleableView>
    <Distance />
    <BatteryIndicator />
  </div>
</template>

<script setup lang="ts">
import {
  onBeforeUnmount,
  defineAsyncComponent,
  computed,
  onMounted,
} from "vue";
import { RouterView } from "vue-router";
import ToggleableView from "@/ui/ToggleableView.vue";
import Messager from "@/features/messager/Messager.vue";
import LazySettings from "@/features/settings/LazySettings.vue";
import { useSettingsStore, usePopupStore } from "@/features/settings/stores";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import { useAppHeight } from "@/composables/useAppHeight";
import { useAppSyncStore } from "@/features/syncer/store";

const popupStore = usePopupStore();
const syncStore = useAppSyncStore();
const isMobile = useDeviceWatcher();

const settingsStore = useSettingsStore();
const isSettingsLoaded = computed(() => settingsStore.loaded);
const isPopupOpen = computed(() => popupStore.isOpen);

const Distance = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Distance.vue"),
});

const ObjectDetectionSwitch = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/ObjectDetectionSwitch.vue"),
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

useAppHeight();

onMounted(() => {
  syncStore.initializeWebSocket();
});
onBeforeUnmount(() => {
  syncStore.cleanup();
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
