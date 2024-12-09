<template>
  <div class="record-indicator" v-if="isRecording">
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

<style scoped lang="scss">
@use "@/assets/scss/blink";

.record-indicator {
  color: var(--color-text);

  .btn {
    padding: 0.2rem 0.8rem;
    font-size: 20px;
    letter-spacing: 1px;
    font-family: var(--font-family);
    cursor: pointer;
    color: var(--color-text);
    border: none;
    background-color: transparent;
    outline: none;
    transition: all 0.3s ease;
    &:hover {
      opacity: 0.7;
    }
  }
}
</style>
