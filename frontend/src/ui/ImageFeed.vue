<template>
  <ScanLines
    v-if="!active"
    class="scan"
    :class="{
      'scan-full': !imgInitted,
    }"
  />
  <img
    v-else
    ref="imgRef"
    class="image-feed"
    :draggable="false"
    @load="handleImageOnLoad"
    :class="{
      loading: imgLoading,
    }"
    alt="Video"
  />
  <canvas
    v-if="objectDetectionIsOn && active"
    ref="overlayCanvas"
    class="overlay-canvas"
  ></canvas>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, watch, onMounted, computed } from "vue";
import ScanLines from "@/ui/ScanLines.vue";
import { useWebsocketStream } from "@/composables/useWebsocketStream";
import { useCameraRotate } from "@/composables/useCameraRotate";
import {
  useCameraStore,
  useDetectionStore,
  useStreamStore,
} from "@/features/settings/stores";
import { drawOverlay, drawAimOverlay } from "@/util/overlay";

const camStore = useCameraStore();
const detectionStore = useDetectionStore();
const streamStore = useStreamStore();
const overlayCanvas = ref<HTMLCanvasElement | null>(null);

const listenersAdded = ref(false);

const objectDetectionIsOn = computed(() => detectionStore.data.active);

const {
  initWS,
  cleanup,
  imgRef,
  handleImageOnLoad,
  imgLoading,
  active,
  imgInitted,
} = useWebsocketStream({ url: "ws/video-stream" });

const { addListeners, removeListeners } = useCameraRotate(imgRef);

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

      const handler =
        streamStore.data.enhance_mode === "robocop_vision"
          ? drawAimOverlay
          : drawOverlay;
      if (timeDiff >= 0 && timeDiff <= 0.6) {
        handler(overlayCanvas.value, imgRef.value, newResults);
      } else {
        handler(overlayCanvas.value, imgRef.value, []);
      }
    }
  },
);

watch(
  () => imgRef.value,
  (el) => {
    if (el && !listenersAdded.value) {
      addListeners();
      listenersAdded.value = true;
    }
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
  cleanup();
};

onMounted(async () => {
  await camStore.fetchAllCameraSettings();
  initWS();
  if (detectionStore.data.active) {
    detectionStore.initializeWebSocket();
  }
  addListeners();
  window.addEventListener("beforeunload", handleSocketsCleanup);
});

onBeforeUnmount(() => {
  listenersAdded.value = false;
  removeListeners();
  handleSocketsCleanup();
});
</script>

<style scoped lang="scss">
.image-feed {
  width: 100%;
  display: block;
  height: 99%;
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);
  user-select: none;
  cursor: grab;
  touch-action: none;
}
.loading {
  opacity: 0;
}

.scan {
  width: 100%;
}
.scan-full {
  height: 90%;
}
.overlay-canvas {
  position: absolute;
  left: 0;
  height: 99%;
  pointer-events: none;
}
</style>
