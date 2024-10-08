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
    @load="handleImageOnLoad"
    :class="{
      loading: imgLoading,
    }"
    alt="Video"
  />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import ScanLines from "@/ui/ScanLines.vue";
import { makeWebsocketUrl } from "@/util/url";
import { useWebsocketStream } from "@/composables/useWebsocketStream";
import { useCameraStore } from "@/features/settings/stores";

const camStore = useCameraStore();

const fetchSettttings = async () => {
  await camStore.fetchCurrentSettings();
};

const {
  initWS,
  closeWS,
  imgRef,
  handleImageOnLoad,
  imgLoading,
  connected,
  imgInitted,
} = useWebsocketStream(makeWebsocketUrl("ws/video-stream"), {
  onFirstMessage: () => {
    fetchSettttings();
    console.log("onFirstMessage: Fetch camera settttings");
  },
});

onMounted(() => {
  fetchSettttings();
  initWS();
  window.addEventListener("beforeunload", closeWS);
});
onUnmounted(() => {
  closeWS();
  window.removeEventListener("beforeunload", closeWS);
});
</script>

<style scoped lang="scss">
.image-feed {
  width: 100%;
  display: block;
  height: 99%;
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);
  user-select: none;
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
