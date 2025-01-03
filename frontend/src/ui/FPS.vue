<template>
  <span v-if="fpsStore.fps" class="bold" :class="class">
    {{ fps }}&nbsp;FPS
  </span>
</template>

<script setup lang="ts">
import { useFPSStore } from "@/features/settings/stores";
import { computed } from "vue";

defineProps<{ class?: string }>();

const fpsStore = useFPSStore();

const fps = computed(() => fpsStore.fps);
</script>
