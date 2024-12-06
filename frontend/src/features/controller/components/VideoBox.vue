<template>
  <ResizableContainer
    :isResizable="isResizable && !isMobile"
    fullscreen
    :default-width="defaultWidth"
    :default-height="defaultHeight"
  >
    <ImageFeed />
  </ResizableContainer>
</template>
<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import { usePopupStore, useCameraStore } from "@/features/settings/stores";
import ResizableContainer from "@/ui/ResizableContainer.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";

const isMobile = useDeviceWatcher();

const ImageFeed = defineAsyncComponent({
  loader: () => import("@/ui/ImageFeed.vue"),
});

const popupStore = usePopupStore();
const cameraStore = useCameraStore();

const defaultWidth = computed(() => cameraStore.data.width);
const defaultHeight = computed(() => cameraStore.data.height);

const isResizable = computed(() => !popupStore.isOpen);
</script>

<style scoped lang="scss"></style>
