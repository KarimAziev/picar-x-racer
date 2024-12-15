<template>
  <KeyboardHandler v-if="!isMobile && isSettingsLoaded" />
  <JoysticZone v-if="isMobile && isSettingsLoaded" />
  <RouterView />
  <LazySettings />
  <Messager v-if="!isMobile" />
  <TopRightPanel class="flex flex-col bold text-align-right">
    <BatteryIndicator v-if="isSettingsLoaded" />
    <ActiveConnectionsIndicator v-if="!isMobile && isSettingsLoaded" />
  </TopRightPanel>
  <div class="indicators" v-if="isSettingsLoaded">
    <ActiveConnectionsIndicator v-if="isMobile && isSettingsLoaded" />
    <Recording />
    <ToggleableView setting="show_object_detection_settings">
      <DetectionControls />
    </ToggleableView>
    <CalibrationModeInfo v-if="!isMobile" />
    <div v-if="!isMobile" class="flex flex-wrap align-items-center">
      <ToggleableView setting="text_to_speech_input">
        <TextToSpeechInput />
      </ToggleableView>
      <AudioStream />
      <PhotoButton />
    </div>
    <ToggleableView setting="show_player">
      <MusicPlayer />
    </ToggleableView>
    <Distance v-if="!isMobile" />
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

const AudioStream = defineAsyncComponent({
  loader: () => import("@/ui/AudioStream.vue"),
});

const PhotoButton = defineAsyncComponent({
  loader: () => import("@/ui/PhotoButton.vue"),
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

const TextToSpeechInput = defineAsyncComponent({
  loader: () => import("@/ui/tts/TextToSpeechInput.vue"),
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
const Recording = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/camera/VideoRecordingIndicator.vue"),
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
