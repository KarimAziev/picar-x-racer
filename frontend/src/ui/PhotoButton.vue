<template>
  <Button
    class="opacity-hover"
    @click="controllerStore.takePhoto"
    icon="pi pi-camera"
    :loading="cameraStore.capturing"
    :disabled="cameraStore.capturing"
    text
    aria-label="capture-photo"
    v-tooltip="'Capture a photo'"
  />
</template>

<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import { useCameraStore } from "@/features/settings/stores";

defineProps<{ class?: string }>();

const controllerStore = useControllerStore();
const cameraStore = useCameraStore();
</script>
