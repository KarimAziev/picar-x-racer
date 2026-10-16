<template>
  <ScanLines v-if="!isVideoVisible" class="w-full h-[99%]">
    <div
      class="text-center text-error text-xl font-black absolute inset-0 flex items-center justify-center uppercase"
    >
      {{ errorMsg }}
    </div>
  </ScanLines>
  <img
    v-show="isVideoVisible"
    ref="imgRef"
    class="w-full block h-[99%] shadow-[0_0_4px_2px] shadow-primary-500 select-none cursor-grab touch-none"
    :draggable="false"
    @load="handleImageOnLoad"
    :class="props.imgClass"
    alt="Video"
  />
  <canvas
    v-if="isOverlayEnabled"
    ref="overlayCanvas"
    class="absolute left-0 h-[99%] pointer-events-none"
  ></canvas>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, watch, onMounted, computed } from "vue";
import { useCssVar } from "@vueuse/core";
import ScanLines from "@/ui/ScanLines.vue";
import { useCameraRotate } from "@/composables/useCameraRotate";
import { useCameraStore, useThemeStore } from "@/features/settings/stores";
import { useDetectionStore, useWebsocketStream } from "@/features/detection";
import { drawOverlay } from "@/features/detection/overlays/overlay";
import { overlayStyleHandlers } from "@/features/detection/config";
import type { DetectionResult } from "@/features/detection/interface";

const props = defineProps<{ imgClass?: string }>();

const camStore = useCameraStore();
const detectionStore = useDetectionStore();
const themeStore = useThemeStore();
const overlayCanvas = ref<HTMLCanvasElement | null>(null);

const imgRef = ref<HTMLImageElement>();

const errorMsg = computed(() => camStore.error);

const {
  initWS: initVideoStreamWS,
  cleanup: cleanupVideoStreamWS,
  handleImageOnLoad,
  imgLoading,
  active: isVideoStreamActive,
} = useWebsocketStream({ url: "api/ws/video-stream", imgRef });

const isVideoVisible = computed(
  () => isVideoStreamActive.value && !imgLoading.value && !errorMsg.value,
);

const isOverlayEnabled = computed(
  () => detectionStore.data.active && isVideoVisible.value,
);

const font = useCssVar("--canvas-font");
const colorText = useCssVar("--color-text");
let overlayAnimationFrame: number | null = null;
let disposed = false;

const {
  addListeners: addCameraRotateListeners,
  removeListeners: removeCameraRotateListeners,
} = useCameraRotate(imgRef);

const drawDetectionResults = (newResults: DetectionResult[]) => {
  if (!overlayCanvas.value || !imgRef.value) {
    return;
  }

  const frameTimeStamp = detectionStore.currentFrameTimestamp;
  const detectionTimeStamp = detectionStore.timestamp;

  const enabled = detectionTimeStamp && frameTimeStamp;

  if (!enabled) {
    return drawOverlay(overlayCanvas.value, imgRef.value, []);
  }
  const timeDiff = frameTimeStamp - detectionTimeStamp;
  const handler = overlayStyleHandlers[detectionStore.data.overlay_style];
  if (timeDiff <= detectionStore.data.overlay_draw_threshold) {
    handler(
      overlayCanvas.value,
      imgRef.value,
      newResults,
      font.value,
      themeStore.bboxesColor || colorText.value,
      themeStore.lines,
      themeStore.keypoints,
      detectionStore.semantic_mask,
      detectionStore.data.keypoint_confidence_threshold,
    );
  } else {
    handler(overlayCanvas.value, imgRef.value, []);
  }
};

const scheduleOverlayDraw = (newResults: DetectionResult[]) => {
  if (overlayAnimationFrame !== null) {
    cancelAnimationFrame(overlayAnimationFrame);
  }
  overlayAnimationFrame = requestAnimationFrame(() => {
    overlayAnimationFrame = null;
    drawDetectionResults(newResults);
  });
};

watch(
  () => detectionStore.detection_result,
  (newResults) => {
    scheduleOverlayDraw(newResults);
  },
);

watch(
  () => detectionStore.data.overlay_style,
  () => {
    scheduleOverlayDraw(detectionStore.detection_result);
  },
);

watch(
  () => detectionStore.semantic_mask,
  () => {
    scheduleOverlayDraw(detectionStore.detection_result);
  },
);

watch(isOverlayEnabled, (enabled) => {
  if (!enabled && overlayCanvas.value && imgRef.value) {
    if (overlayAnimationFrame !== null) {
      cancelAnimationFrame(overlayAnimationFrame);
      overlayAnimationFrame = null;
    }
    drawOverlay(overlayCanvas.value, imgRef.value, []);
  }
});

watch(
  () => imgRef.value,
  () => {
    addCameraRotateListeners();
  },
);

watch(
  () => detectionStore.data.active,
  (mode) => {
    if (mode && !detectionStore.connecting && !detectionStore.connected) {
      detectionStore.initializeWebSocket();
    } else if (!mode) {
      detectionStore.cleanup();
    }
  },
);

const handleSocketsCleanup = () => {
  window.removeEventListener("beforeunload", handleSocketsCleanup);
  detectionStore.cleanup();
  cleanupVideoStreamWS();
};

onMounted(async () => {
  await camStore.fetchAllCameraSettings();
  if (disposed) {
    return;
  }
  initVideoStreamWS();
  if (detectionStore.data.active) {
    detectionStore.initializeWebSocket();
  }

  if (imgRef.value) {
    addCameraRotateListeners();
  }
  window.addEventListener("beforeunload", handleSocketsCleanup);
});

onBeforeUnmount(() => {
  disposed = true;
  if (overlayAnimationFrame !== null) {
    cancelAnimationFrame(overlayAnimationFrame);
  }
  removeCameraRotateListeners();
  handleSocketsCleanup();
});
</script>
