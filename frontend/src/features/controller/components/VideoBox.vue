<template>
  <FullscreenToggle />
  <ResizableContainer
    :isResizable="isResizable && !isMobile"
    :fullscreen="fullscreen"
    :default-width="defaultWidth"
    :default-height="defaultHeight"
  >
    <ImageFeed />
  </ResizableContainer>
</template>
<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import {
  usePopupStore,
  useSettingsStore,
  useCameraStore,
} from "@/features/settings/stores";
import FullscreenToggle from "@/features/controller/components/FullscreenToggle.vue";
import ResizableContainer from "@/ui/ResizableContainer.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";

const isMobile = useDeviceWatcher();

const ImageFeed = defineAsyncComponent({
  loader: () => import("@/ui/ImageFeed.vue"),
});

const popupStore = usePopupStore();
const settingsStore = useSettingsStore();
const cameraStore = useCameraStore();

const fullscreen = computed(() => settingsStore.settings.fullscreen);
const defaultWidth = computed(() => cameraStore.data.video_feed_width);
const defaultHeight = computed(() => cameraStore.data.video_feed_height);

const isResizable = computed(() => !popupStore.isOpen);
</script>

<style scoped lang="scss"></style>
