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
import { usePopupStore, useSettingsStore } from "@/features/settings/stores";
import FullscreenToggle from "@/features/controller/components/FullscreenToggle.vue";
import ResizableContainer from "@/ui/ResizableContainer.vue";

const ImageFeed = defineAsyncComponent({
  loader: () => import("@/ui/ImageFeed.vue"),
});

const popupStore = usePopupStore();
const settingsStore = useSettingsStore();

const fullscreen = computed(() => settingsStore.settings.fullscreen);
const isResizable = computed(() => !popupStore.isOpen);
const [defaultWidth, defaultHeight] = [1280, 720];
</script>

<style scoped lang="scss"></style>
