<template>
  <ResizableContainer
    :isResizable="isResizable && !isMobile"
    fullscreen
    :default-width="defaultWidth"
    :default-height="defaultHeight"
  >
    <ImageFeed v-if="!hideCamera" :imgClass="imgClass" />
    <img
      v-else
      :class="imgClass"
      src="@/assets/logo.svg"
      class="w-full block h-[99%] shadow-[0_0_4px_2px] shadow-primary-500 select-none cursor-grab touch-none"
    />
  </ResizableContainer>
</template>
<script setup lang="ts">
import { computed, defineAsyncComponent, inject } from "vue";
import { rotationClasses } from "@/features/settings/components/camera/config";
import {
  usePopupStore,
  useCameraStore,
  useStreamStore,
} from "@/features/settings/stores";
import ResizableContainer from "@/ui/ResizableContainer.vue";
import type { Ref } from "vue";

const isMobile = inject<Ref<boolean, boolean>>("isMobile");

const hideCamera = import.meta.env.VITE_USE_CAMERA === "false";

const ImageFeed = defineAsyncComponent({
  loader: () => import("@/ui/ImageFeed.vue"),
});

const popupStore = usePopupStore();
const streamStore = useStreamStore();
const cameraStore = useCameraStore();
const rotation = computed(() => streamStore.data.rotation);

const imgClass = computed(() => {
  if (!rotation.value || !rotationClasses[rotation.value]) {
    return;
  }
  return rotationClasses[rotation.value];
});

const flipWidthHeight = computed(
  () => streamStore.data.rotation === 90 || streamStore.data.rotation === 270,
);
const defaultWidth = computed(() =>
  flipWidthHeight.value ? cameraStore.data.height : cameraStore.data.width,
);
const defaultHeight = computed(() =>
  flipWidthHeight.value ? cameraStore.data.width : cameraStore.data.height,
);

const isResizable = computed(() => !popupStore.isOpen);
</script>
