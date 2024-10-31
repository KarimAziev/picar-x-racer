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
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, watch, onMounted } from "vue";
import ScanLines from "@/ui/ScanLines.vue";
import { makeWebsocketUrl } from "@/util/url";
import { useWebsocketStream } from "@/composables/useWebsocketStream";
import { useCameraStore } from "@/features/settings/stores";
import { useCameraRotate } from "@/composables/useCameraRotate";

const camStore = useCameraStore();

const fetchSettings = async () => {
  await camStore.fetchCurrentSettings();
};

const listenersAdded = ref(false);

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
  () => imgRef.value,
  (el) => {
    if (el && !listenersAdded.value) {
      addListeners();
      listenersAdded.value = true;
    }
  },
);

onMounted(() => {
  fetchSettings();
  initWS();
  addListeners();
  window.addEventListener("beforeunload", closeWS);
});

onBeforeUnmount(() => {
  listenersAdded.value = false;
  removeListeners();
  window.removeEventListener("beforeunload", closeWS);
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
  touch-action: manipulation;
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
</style>
