<template>
  <div
    class="px-3 py-1 text-robo-color-primary bg-transparent border-none outline-none cursor-pointer uppercase tracking-widest hover:opacity-70 animate-pulse font-tt-octosquares"
    v-if="isRecording"
  >
    <button @click="handleToggle" text class="btn blink">RECORD</button>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useStreamStore } from "@/features/settings/stores";

const streamStore = useStreamStore();

const isRecording = computed(() => streamStore.data.video_record);

const handleToggle = async () => {
  await streamStore.toggleRecording();
};
</script>
