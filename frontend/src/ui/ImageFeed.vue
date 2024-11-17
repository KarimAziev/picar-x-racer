<template>
  <ScanLines
    v-if="!connected"
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
    v-if="objectDetectionIsOn"
    ref="overlayCanvas"
    class="overlay-canvas"
  ></canvas>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, watch, onMounted, computed } from "vue";
import ScanLines from "@/ui/ScanLines.vue";
import { makeWebsocketUrl } from "@/util/url";
import { useWebsocketStream } from "@/composables/useWebsocketStream";
import { useCameraStore, useSettingsStore } from "@/features/settings/stores";
import { useCameraRotate } from "@/composables/useCameraRotate";
import { useDetectionStore } from "@/features/controller/detectionStore";
import { drawOverlay, drawAimOverlay } from "@/util/overlay";

const settingsStore = useSettingsStore();
const camStore = useCameraStore();
const detectionStore = useDetectionStore();
const overlayCanvas = ref<HTMLCanvasElement | null>(null);

const listenersAdded = ref(false);

const objectDetectionIsOn = computed(
  () => camStore.data.video_feed_object_detection,
);

const {
  initWS,
  closeWS,
  imgRef,
  handleImageOnLoad,
  imgLoading,
  connected,
  imgInitted,
} = useWebsocketStream(makeWebsocketUrl("ws/video-stream"));

const { addListeners, removeListeners } = useCameraRotate(imgRef);

watch(
  () => detectionStore.detection_result,
  (newResults) => {
    if (overlayCanvas.value && imgRef.value) {
      const frameTimeStamp = detectionStore.currentFrameTimestamp;
      const detectionTimeStamp = detectionStore.timestamp;
      const enabled =
        detectionTimeStamp &&
        frameTimeStamp &&
        detectionTimeStamp <= frameTimeStamp;

      if (enabled) {
        const handler =
          settingsStore.settings.video_feed_enhance_mode === "robocop_vision"
            ? drawAimOverlay
            : drawOverlay;
        handler(overlayCanvas.value, imgRef.value, newResults);
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
  () => camStore.data.video_feed_detect_mode,
  (mode) => {
    if (mode && !detectionStore.connected && !detectionStore.loading) {
      detectionStore.initializeWebSocket();
    } else if (!mode) {
      detectionStore.cleanup();
    }
  },
);

onMounted(async () => {
  await camStore.fetchAllCameraSettings();
  initWS();
  if (camStore.data.video_feed_detect_mode) {
    detectionStore.initializeWebSocket();
  }
  addListeners();
  window.addEventListener("beforeunload", closeWS);
});

onBeforeUnmount(() => {
  listenersAdded.value = false;
  removeListeners();
  window.removeEventListener("beforeunload", closeWS);
  detectionStore.cleanup();
  closeWS();
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
