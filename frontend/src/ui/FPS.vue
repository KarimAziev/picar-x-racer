<template>
  <span v-if="fps !== null" class="bold" :class="class">
    {{ fps }}&nbsp;FPS
  </span>
  <span v-if="serverFPS !== null" class="bold" :class="class">
    {{ serverFPS }}&nbsp;FPS&nbsp;(Server)
  </span>
</template>

<script setup lang="ts">
import { useFPSStore } from "@/features/settings/stores";
import { computed } from "vue";

defineProps<{ class?: string }>();

const fpsStore = useFPSStore();

const fps = computed(() => fpsStore.fps);
const serverFPS = computed(() => fpsStore.serverFPS);
</script>
