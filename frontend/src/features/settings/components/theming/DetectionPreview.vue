<template>
  <div ref="canvasWrapper" class="w-full h-[480px] relative"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import { DetectionPoseRenderer } from "@/features/detection/overlays/pose/DetectionPoseRenderer";
import { detectionSample } from "@/features/settings/components/theming/config";
import { useThemeStore } from "@/features/settings/stores";
import { useElementSize } from "@/composables/useElementSize";

const store = useThemeStore();

const canvasWrapper = ref<HTMLElement | null>(null);
const rendererInstance = ref<DetectionPoseRenderer | null>(null);
const wrapperSize = useElementSize(canvasWrapper);

onMounted(() => {
  if (canvasWrapper.value) {
    rendererInstance.value = new DetectionPoseRenderer(
      canvasWrapper.value,
      14,
      wrapperSize.width,
      wrapperSize.height,
    );

    rendererInstance.value.renderDetections(
      [detectionSample],
      store.lines,
      store.keypoints,
      store.bboxesColor,
    );
    rendererInstance.value.alignToCenter();
  }
});

watch(
  () => [
    wrapperSize.width,
    wrapperSize.height,
    store.primaryColor,
    store.bboxesColor,
    store.dark,
    store.lines,
    store.keypoints,
  ],
  () => {
    if (rendererInstance.value) {
      rendererInstance.value.setSize(wrapperSize.width, wrapperSize.height);
      rendererInstance.value.renderDetections(
        [detectionSample],
        store.lines,
        store.keypoints,
        store.bboxesColor,
      );
    }
  },
  { deep: true },
);

onBeforeUnmount(() => {
  rendererInstance.value?.dispose();
});
</script>
