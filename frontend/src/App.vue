<template>
  <KeyboardHandler v-if="!isMobile && isSettingsLoaded" />
  <JoysticZone v-if="isMobile && isSettingsLoaded" />
  <RouterView />
  <LazySettings />
  <Messager v-if="!isMobile" />
  <TopRightPanel v-if="isSettingsLoaded" class="top-right-pan">
    <ToggleableView setting="stream.render_fps">
      <FPS />
    </ToggleableView>
    <PowerControlPanel>
      <ToggleableView setting="general.show_fullscreen_button">
        <FullscreenButton />
      </ToggleableView>
      <ToggleableView setting="general.show_connections_indicator">
        <ActiveConnectionsIndicator />
      </ToggleableView>
    </PowerControlPanel>
  </TopRightPanel>
  <div class="indicators" v-if="!isMobile && isSettingsLoaded">
    <MediaControls />
    <ToggleableView setting="general.show_object_detection_settings">
      <DetectionControls />
    </ToggleableView>
    <CalibrationModeInfo />
    <ToggleableView setting="general.text_to_speech_input">
      <TextToSpeechInput />
    </ToggleableView>
    <ToggleableView setting="general.show_player">
      <MusicPlayer />
    </ToggleableView>
  </div>
  <div class="mobile-indicators" v-if="isMobile && isSettingsLoaded">
    <ToggleableView setting="general.show_object_detection_settings">
      <DetectionControls />
    </ToggleableView>
    <ToggleableView setting="general.show_player">
      <MusicPlayer />
    </ToggleableView>
  </div>
</template>

<script setup lang="ts">
import {
  onBeforeUnmount,
  defineAsyncComponent,
  computed,
  onMounted,
  onBeforeMount,
} from "vue";
import { RouterView } from "vue-router";
import Messager from "@/features/messager/components/Messager.vue";
import LazySettings from "@/features/settings/LazySettings.vue";
import { useSettingsStore, useThemeStore } from "@/features/settings/stores";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import { useAppHeight } from "@/composables/useAppHeight";
import { useAppSyncStore } from "@/features/syncer";

import ToggleableView from "@/ui/ToggleableView.vue";
import TopRightPanel from "@/ui/TopRightPanel.vue";
import FPS from "@/ui/FPS.vue";

const syncStore = useAppSyncStore();
const isMobile = useDeviceWatcher();

const settingsStore = useSettingsStore();
const isSettingsLoaded = computed(() => settingsStore.loaded);

const themeStore = useThemeStore();

const ActiveConnectionsIndicator = defineAsyncComponent({
  loader: () =>
    import("@/features/syncer/components/ActiveConnectionsIndicator.vue"),
});

const FullscreenButton = defineAsyncComponent({
  loader: () => import("@/ui/FullscreenButton.vue"),
});

const PowerControlPanel = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/system/PowerControlPanel.vue"),
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

const DetectionControls = defineAsyncComponent({
  loader: () => import("@/features/detection/components/DetectionControls.vue"),
});

const MusicPlayer = defineAsyncComponent({
  loader: () => import("@/features/music/components/MusicPlayer.vue"),
});

const CalibrationModeInfo = defineAsyncComponent({
  loader: () =>
    import("@/features/controller/components/CalibrationModeInfo.vue"),
});

const JoysticZone = defineAsyncComponent({
  loader: () => import("@/features/joystick/components/JoysticZone.vue"),
});

useAppHeight();

onBeforeMount(themeStore.init);

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

  @media (max-width: 992px) {
    right: 10px;
    top: 20px;
  }

  @media (min-width: 992px) {
    padding: 0 10px;
    left: 0;
    bottom: 0;
  }

  @media (max-width: 992px) and (min-height: 375px) {
    top: 25px;
  }

  @media (max-width: 768px) {
    max-width: 190px;
  }

  @media (max-width: 992px) {
    max-width: 200px;
  }
}
.mobile-indicators {
  position: absolute;
  z-index: 11;
  text-align: left;
  user-select: none;
  right: 10px;
  top: 20px;

  @media (max-width: 992px) and (min-height: 375px) {
    top: 25px;
  }

  @media (max-width: 768px) {
    max-width: 190px;
  }

  @media (max-width: 992px) {
    max-width: 200px;
  }
}
.top-right-pan {
  @media (max-width: 992px) {
    font-size: 0.8rem;
  }
}
</style>
