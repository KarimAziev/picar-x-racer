<template>
  <ScanLines
    v-if="!isVideoStreamActive || errorMsg"
    class="w-full"
    :class="{
      'h-[90%]': !imgInitted && !errorMsg,
    }"
  >
    <div
      class="text-center text-error text-xl font-black absolute inset-0 flex items-center justify-center uppercase"
    >
      {{ errorMsg }}
    </div>
  </ScanLines>
  <img
    v-else
    ref="imgRef"
    class="w-full block h-[99%] shadow-[0_0_4px_2px] shadow-primary-500 select-none cursor-grab touch-none"
    :draggable="false"
    @load="handleImageOnLoad"
    :class="imgClass"
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
  imgInitted,
} = useWebsocketStream({ url: "api/ws/video-stream", imgRef });

const imgClass = computed(() => ({
  "opacity-0": imgLoading.value,
  [props.imgClass || ""]: !!props.imgClass,
}));

const isOverlayEnabled = computed(
  () => detectionStore.data.active && isVideoStreamActive.value,
);

const font = useCssVar("--canvas-font");
const colorText = useCssVar("--color-text");

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
        handler(
          overlayCanvas.value,
          imgRef.value,
          newResults,
          font.value,
          themeStore.bboxesColor || colorText.value,
          themeStore.lines,
          themeStore.keypoints,
        );
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
