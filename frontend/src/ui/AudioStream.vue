<template>
  <div class="audio-stream">
    <Button
      size="small"
      text
      @click="startAudio"
      :disabled="loading"
      v-if="!connected"
    >
      {{ connected ? "Audio Streaming Active" : "Start Audio Stream" }}
    </Button>
    <Button size="small" text @click="stopAudio" v-if="connected"
      >Stop Audio Stream</Button
    >
  </div>
</template>

<script setup lang="ts">
import { useWebsocketAudio } from "@/composables/useAudioStream";
import Button from "primevue/button";

const { startAudio, stopAudio, connected, loading } =
  useWebsocketAudio("ws/audio-stream");
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
