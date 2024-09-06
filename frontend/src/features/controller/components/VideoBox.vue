<template>
  <FullscreenToggle />
  <ResizableContainer
    :isResizable="isResizable"
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

const ImageFeed = defineAsyncComponent({
  loader: () => import("@/ui/ImageFeed.vue"),
});

const popupStore = usePopupStore();
const settingsStore = useSettingsStore();
const cameraStore = useCameraStore();

const fullscreen = computed(() => settingsStore.settings.fullscreen);
const defaultWidth = computed(() => cameraStore.data.width || 640);
const defaultHeight = computed(() => cameraStore.data.height || 480);
const isResizable = computed(() => !popupStore.isOpen);
</script>

<style scoped lang="scss"></style>
