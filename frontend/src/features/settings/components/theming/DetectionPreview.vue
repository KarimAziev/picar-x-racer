<template>
  <div
    class="w-full h-[380px] bg-black relative overflow-hidden"
    ref="canvasWrapper"
  >
    <canvas
      ref="overlayCanvas"
      class="absolute left-0 h-[99%] pointer-events-none"
    ></canvas>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch, useTemplateRef } from "vue";
import { useThemeStore } from "@/features/settings/stores";
import { drawOverlay } from "@/util/overlay";
import { detectionSample } from "@/features/settings/components/theming/config";
import { useElementSize } from "@/composables/useElementSize";

const store = useThemeStore();
const canvasWrapper = useTemplateRef("canvasWrapper");
const overlayCanvas = useTemplateRef("overlayCanvas");
const wrapperSize = useElementSize(canvasWrapper);

const handleRenderSkeletonPreview = () => {
  if (!overlayCanvas.value || !canvasWrapper.value) {
    return;
  }

  const canvasWidth = wrapperSize.width;

  const [origLeft, top, origRight, bottom] = detectionSample.bbox;
  const detectionWidth = origRight - origLeft;
  const offsetX = (canvasWidth - detectionWidth) / 2;

  const adjustedBbox: [number, number, number, number] = [
    offsetX,
    top,
    offsetX + detectionWidth,
    bottom,
  ];
  const adjustedKeypoints = detectionSample.keypoints.map((point) => ({
    ...point,
    x: point.x - origLeft + offsetX,
  }));

  canvasWrapper.value.style.height = `${detectionSample.bbox[3] + 30}`;
  drawOverlay(
    overlayCanvas.value,
    canvasWrapper.value,
    [
      {
        ...detectionSample,
        bbox: adjustedBbox,
        keypoints: adjustedKeypoints,
      },
    ],
    "14px TT-Octosquares-Regular",
    store.bboxesColor,
    store.lines,
    store.keypoints,
    store.skeletonFiber,
  );
};

watch(
  () => [
    store.bboxesColor,
    store.skeletonColor,
    store.keypointsColor,
    store.lines,
    store.keypoints,
    store.skeletonFiber,
    wrapperSize.width,
    wrapperSize.height,
  ],
  () => {
    handleRenderSkeletonPreview();
  },
  { deep: true },
);
onMounted(() => {
  handleRenderSkeletonPreview();
});
</script>
