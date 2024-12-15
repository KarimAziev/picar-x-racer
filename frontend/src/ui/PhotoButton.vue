<template>
  <Button
    class="opacity-hover"
    @click="controllerStore.takePhoto"
    icon="pi pi-camera"
    text
    aria-label="capture-photo"
    v-tooltip="'Capture a photo'"
  />
</template>

<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";

defineProps<{ class?: string }>();

const controllerStore = useControllerStore();
</script>
