<template>
  <KeyboardHandler v-if="!isMobile && isSettingsLoaded" />
  <JoysticZone v-if="isMobile && isSettingsLoaded" />
  <RouterView />
  <LazySettings />
  <Messager v-if="!isMobile" />
  <TopRightPanel
    class="flex flex-col bold text-align-right"
    v-if="isSettingsLoaded"
  >
    <ToggleableView setting="general.show_battery_indicator">
      <BatteryIndicator />
    </ToggleableView>
    <ToggleableView
      setting="general.show_connections_indicator"
      v-if="!isMobile"
    >
      <ActiveConnectionsIndicator />
    </ToggleableView>
  </TopRightPanel>
  <div class="indicators" v-if="isSettingsLoaded">
    <ToggleableView
      setting="general.show_connections_indicator"
      v-if="isMobile"
    >
      <ActiveConnectionsIndicator />
    </ToggleableView>
    <MediaControls v-if="!isMobile" />
    <ToggleableView setting="general.show_object_detection_settings">
      <DetectionControls />
    </ToggleableView>
    <CalibrationModeInfo v-if="!isMobile" />
    <ToggleableView v-if="!isMobile" setting="general.text_to_speech_input">
      <TextToSpeechInput />
    </ToggleableView>
    <ToggleableView setting="general.show_player">
      <MusicPlayer />
    </ToggleableView>
    <ToggleableView setting="general.show_auto_measure_distance_button">
      <Distance v-if="!isMobile" />
    </ToggleableView>
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
import Messager from "@/features/messager/components/Messager.vue";
import LazySettings from "@/features/settings/LazySettings.vue";
import { useSettingsStore } from "@/features/settings/stores";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import { useAppHeight } from "@/composables/useAppHeight";
import { useAppSyncStore } from "@/features/syncer";

import ToggleableView from "@/ui/ToggleableView.vue";
import TopRightPanel from "@/ui/TopRightPanel.vue";

const syncStore = useAppSyncStore();
const isMobile = useDeviceWatcher();

const settingsStore = useSettingsStore();
const isSettingsLoaded = computed(() => settingsStore.loaded);

const ActiveConnectionsIndicator = defineAsyncComponent({
  loader: () =>
    import("@/features/syncer/components/ActiveConnectionsIndicator.vue"),
});

const TextToSpeechInput = defineAsyncComponent({
  loader: () => import("@/ui/tts/TextToSpeechInput.vue"),
});

const MediaControls = defineAsyncComponent({
  loader: () => import("@/ui/MediaControls.vue"),
});

const KeyboardHandler = defineAsyncComponent({
  loader: () => import("@/features/controller/components/KeyboardHandler.vue"),
});

const Distance = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Distance.vue"),
});

const DetectionControls = defineAsyncComponent({
  loader: () => import("@/features/detection/components/DetectionControls.vue"),
});

const MusicPlayer = defineAsyncComponent({
  loader: () => import("@/features/music/components/MusicPlayer.vue"),
});

const BatteryIndicator = defineAsyncComponent({
  loader: () => import("@/ui/BatteryIndicator.vue"),
});
const CalibrationModeInfo = defineAsyncComponent({
  loader: () =>
    import("@/features/controller/components/CalibrationModeInfo.vue"),
});

const JoysticZone = defineAsyncComponent({
  loader: () => import("@/features/joystick/components/JoysticZone.vue"),
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
  z-index: 11;
  text-align: left;
  user-select: none;

  @media (min-width: 992px) {
    left: 0;
    bottom: 0;
  }

  @media (max-width: 992px) {
    right: 10px;
    top: 5px;
    max-width: 190px;
  }
}
</style>
