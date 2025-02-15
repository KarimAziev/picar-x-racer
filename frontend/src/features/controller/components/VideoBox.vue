<template>
  <ResizableContainer
    :isResizable="isResizable && !isMobile"
    fullscreen
    :default-width="defaultWidth"
    :default-height="defaultHeight"
  >
    <ImageFeed v-if="!hideCamera" />
    <img
      v-else
      src="@/assets/logo.svg"
      class="w-full block h-[99%] shadow-[0_0_4px_2px] shadow-primary-500 select-none cursor-grab touch-none"
    />
  </ResizableContainer>
</template>
<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import { usePopupStore, useCameraStore } from "@/features/settings/stores";
import ResizableContainer from "@/ui/ResizableContainer.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";

const isMobile = useDeviceWatcher();

const hideCamera = import.meta.env.VITE_USE_CAMERA === "false";

const ImageFeed = defineAsyncComponent({
  loader: () => import("@/ui/ImageFeed.vue"),
});

const popupStore = usePopupStore();
const cameraStore = useCameraStore();

const defaultWidth = computed(() => cameraStore.data.width);
const defaultHeight = computed(() => cameraStore.data.height);

const isResizable = computed(() => !popupStore.isOpen);
</script>
