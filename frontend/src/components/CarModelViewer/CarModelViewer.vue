<template>
  <div ref="rootElement" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { useControllerStore } from "@/stores/controller";
import { CarModelRenderer } from "@/components/CarModelViewer/CarModelRenderer";

const store = useControllerStore();
const rootElement = ref<HTMLElement | null>(null);
let carVisualization: CarModelRenderer | null = null;

onMounted(() => {
  if (rootElement.value) {
    carVisualization = new CarModelRenderer(rootElement.value);
    carVisualization.updatePan(store.camPan);
    carVisualization.updateTilt(store.camTilt);

    carVisualization.updateServoDir(store.servoAngle);
  }
});

watch(
  () => store.camPan,
  (newVal) => {
    carVisualization?.updatePan(newVal);
  },
);

watch(
  () => store.camTilt,
  (newVal) => {
    carVisualization?.updateTilt(newVal);
  },
);

watch(
  () => store.servoAngle,
  (newVal) => {
    carVisualization?.updateServoDir(newVal);
  },
);

onUnmounted(() => {
  carVisualization = null;
});
</script>
<style scoped lang="scss"></style>
