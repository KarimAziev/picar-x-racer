<template>
  <div class="audio-stream">
    <Button
      size="small"
      text
      @click="musicStore.toggleStreaming"
      :disabled="loading"
    >
      {{ connected ? "Stop Audio Stream" : "Start Audio Stream" }}
    </Button>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch } from "vue";
import { useWebsocketAudio } from "@/composables/useAudioStream";
import Button from "primevue/button";
import { useMusicStore } from "@/features/music";

const musicStore = useMusicStore();

const { startAudio, stopAudio, connected, loading, cleanup } =
  useWebsocketAudio("ws/audio-stream");

watch(
  () => musicStore.isStreaming,
  (newVal) => {
    if (newVal && !connected.value && !loading.value) {
      startAudio();
    } else {
      stopAudio();
    }
  },
);

const handleSocketsCleanup = () => {
  window.removeEventListener("beforeunload", handleSocketsCleanup);
  cleanup();
};

onMounted(() => {
  window.addEventListener("beforeunload", handleSocketsCleanup);
  if (musicStore.isStreaming) {
    startAudio();
  }
});

onBeforeUnmount(() => {
  handleSocketsCleanup();
});
</script>
<style scoped lang="scss">
.audio-stream {
  margin: auto;
  justify-content: center;
  align-items: center;
  flex-direction: column;
}

button {
  white-space: nowrap;
  max-width: 150px;
}
</style>
