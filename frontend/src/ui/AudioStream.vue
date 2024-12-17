<template>
  <Button
    class="stream-btn"
    :class="fieldStreamClass"
    icon="pi pi-microphone"
    text
    aria-label="audio-stream"
    v-tooltip="tooltipText"
    @click="musicStore.toggleStreaming"
    :disabled="loading"
  >
  </Button>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch, computed } from "vue";
import { useWebsocketAudio } from "@/composables/useAudioStream";
import Button from "primevue/button";
import { useMusicStore } from "@/features/music";

const musicStore = useMusicStore();

const fieldStreamClass = computed(
  () => `${connected.value ? "blink" : "opacity-hover"}`,
);

const tooltipText = computed(
  () =>
    `${connected.value ? "Turn off microphone on the robot" : "Turn on microphone on the robot"}`,
);

const { startAudio, stopAudio, connected, loading, cleanup } =
  useWebsocketAudio("ws/audio-stream");

const handleSocketsCleanup = () => {
  window.removeEventListener("beforeunload", handleSocketsCleanup);
  cleanup();
};

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
@use "@/assets/scss/blink";
</style>
