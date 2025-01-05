<template>
  <ScanLines
    v-if="!isVideoStreamActive"
    class="w-full"
    :class="{
      'h-[90%]': !imgInitted,
    }"
  />
  <img
    v-else
    ref="imgRef"
    class="w-full block h-[99%] shadow-[0_0_4px_2px] shadow-primary-500 select-none cursor-grab touch-none"
    :draggable="false"
    @load="handleImageOnLoad"
    :class="{
      'opacity-0': imgLoading,
    }"
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
import ScanLines from "@/ui/ScanLines.vue";
import { useCameraRotate } from "@/composables/useCameraRotate";
import { useCameraStore } from "@/features/settings/stores";
import { drawOverlay } from "@/util/overlay";
import {
  useDetectionStore,
  useWebsocketStream,
  overlayStyleHandlers,
} from "@/features/detection";

const camStore = useCameraStore();
const detectionStore = useDetectionStore();
const overlayCanvas = ref<HTMLCanvasElement | null>(null);

const imgRef = ref<HTMLImageElement>();

const {
  initWS: initVideoStreamWS,
  cleanup: cleanupVideoStreamWS,
  handleImageOnLoad,
  imgLoading,
  active: isVideoStreamActive,
  imgInitted,
} = useWebsocketStream({ url: "api/ws/video-stream", imgRef });

const isOverlayEnabled = computed(
  () => detectionStore.data.active && isVideoStreamActive.value,
);

const {
  addListeners: addCameraRotateListeners,
  removeListeners: removeCameraRotateListeners,
} = useCameraRotate(imgRef);

watch(
  () => detectionStore.detection_result,
  (newResults) => {
    if (overlayCanvas.value && imgRef.value) {
      const frameTimeStamp = detectionStore.currentFrameTimestamp;
      const detectionTimeStamp = detectionStore.timestamp;

      const enabled = detectionTimeStamp && frameTimeStamp;

      if (!enabled) {
        return drawOverlay(overlayCanvas.value, imgRef.value, []);
      }
      const timeDiff = frameTimeStamp - detectionTimeStamp;
      const handler = overlayStyleHandlers[detectionStore.data.overlay_style];
      if (timeDiff <= detectionStore.data.overlay_draw_threshold) {
        handler(overlayCanvas.value, imgRef.value, newResults);
      } else {
        handler(overlayCanvas.value, imgRef.value, []);
      }
    }
  },
);

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
  removeCameraRotateListeners();
  handleSocketsCleanup();
});
</script>
