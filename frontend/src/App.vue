<template>
  <KeyboardHandler v-if="!isMobile && isSettingsLoaded" />
  <SettingsButton />
  <JoysticZone v-if="isMobile && isSettingsLoaded" />
  <RouterView />
  <LazySettings />
  <Messager v-if="!isMobile" />
  <TopRightPanel v-if="isSettingsLoaded" class="text-xs">
    <ToggleableView setting="stream.render_fps">
      <FPS />
    </ToggleableView>
    <ToggleableView setting="general.show_dark_theme_toggle">
      <DarkThemeToggler />
    </ToggleableView>
    <ToggleableView setting="general.show_fullscreen_button">
      <FullscreenButton />
    </ToggleableView>
    <PowerControlPanel>
      <ToggleableView setting="general.show_connections_indicator">
        <ActiveConnectionsIndicator />
      </ToggleableView>
    </PowerControlPanel>
  </TopRightPanel>
  <div
    class="absolute z-11 select-none bottom-0 flex flex-col gap-y-2"
    v-if="!isMobile && isSettingsLoaded"
  >
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
  <div
    class="select-none absolute z-11 flex flex-col gap-y-1 right-1 top-9 portrait:max-w-[53%] portrait:min-[400px]:max-w-[50%] landscape:max-w-[210px]"
    v-if="isMobile && isSettingsLoaded"
  >
    <ToggleableView setting="general.show_object_detection_settings">
      <DetectionControls class="portrait:justify-end" />
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

const syncStore = useAppSyncStore();
const isMobile = useDeviceWatcher();

const settingsStore = useSettingsStore();
const isSettingsLoaded = computed(() => settingsStore.loaded);

const themeStore = useThemeStore();

const ActiveConnectionsIndicator = defineAsyncComponent({
  loader: () =>
    import("@/features/syncer/components/ActiveConnectionsIndicator.vue"),
});

const DarkThemeToggler = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/theming/DarkThemeToggler.vue"),
});

const FPS = defineAsyncComponent({
  loader: () => import("@/ui/FPS.vue"),
});

const FullscreenButton = defineAsyncComponent({
  loader: () => import("@/ui/FullscreenButton.vue"),
});

const SettingsButton = defineAsyncComponent({
  loader: () => import("@/features/settings/components/SettingsButton.vue"),
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
