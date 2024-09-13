<template>
  <ScanLines v-if="imgLoading || !connected" class="scan" />
  <img
    v-else
    ref="imgRef"
    class="image-feed"
    :class="{
      loading: imgLoading,
    }"
    alt="Video"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import ScanLines from "@/ui/ScanLines.vue";

const ws = ref<WebSocket>();
const WS_URL: string = `ws://${window.location.hostname}:${8050}`;
const imgRef = ref();
const imgLoading = ref(true);
const connected = ref(false);
const reconnectedEnabled = ref(true);
const retryTimer = ref<NodeJS.Timeout | null>(null);

const initWS = () => {
  ws.value = new WebSocket(WS_URL);
  if (!ws.value) {
    return;
  }
  ws.value.binaryType = "arraybuffer";

  ws.value.onmessage = (wsMsg: MessageEvent) => {
    connected.value = true;
    imgLoading.value = false;
    const arrayBufferView = new Uint8Array(wsMsg.data);
    const blob = new Blob([arrayBufferView], { type: "image/jpeg" });
    const urlCreator = window.URL || window.webkitURL;
    const imageUrl = urlCreator.createObjectURL(blob);
    (imgRef.value as HTMLImageElement).src = imageUrl;
  };

  ws.value.onclose = (_: CloseEvent) => {
    console.log("closed");
    connected.value = false;
    imgLoading.value = true;
    retryConnection();
  };
};

const retryConnection = () => {
  if (retryTimer.value) {
    clearTimeout(retryTimer.value);
  }
  if (reconnectedEnabled.value && !connected.value) {
    retryTimer.value = setTimeout(() => {
      console.log("Retrying WebSocket connection...");
      initWS();
    }, 5000);
  }
};

onMounted(() => {
  initWS();
});
onUnmounted(() => {
  reconnectedEnabled.value = false;
  if (ws.value) {
    ws.value.close();
  }
});
</script>

<style scoped lang="scss">
.image-feed {
  width: 100%;
  display: block;
  height: 100%;
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);
  user-select: none;
}
.loading {
  opacity: 0;
}
.box {
  opacity: 1;
  width: 100%;
  height: 100%;
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);
  user-select: none;
}
.scan {
  width: 100%;
  height: 100%;
}
</style>
