<template>
  <img
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

const ws = ref<WebSocket>();
const WS_URL: string = `ws://localhost:${8050}`;
const imgRef = ref();
const imgLoading = ref(true);

onMounted(() => {
  ws.value = new WebSocket(WS_URL);
  if (!ws.value) {
    return;
  }
  ws.value.binaryType = "arraybuffer";

  ws.value.onmessage = (wsMsg: MessageEvent) => {
    imgLoading.value = false;
    const arrayBufferView = new Uint8Array(wsMsg.data);
    const blob = new Blob([arrayBufferView], { type: "image/jpeg" });
    const urlCreator = window.URL || window.webkitURL;
    const imageUrl = urlCreator.createObjectURL(blob);
    (imgRef.value as HTMLImageElement).src = imageUrl;
  };

  ws.value.onclose = (_: CloseEvent) => {
    console.log("closed");
  };
});
onUnmounted(() => {
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
</style>
