<template>
  <div ref="rootElement" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { CarModelRenderer } from "@/features/controller/components/CarModelViewer/CarModelRenderer";
import { useControllerStore } from "@/features/controller/store";

const store = useControllerStore();
const rootElement = ref<HTMLElement | null>(null);
let carVisualization: CarModelRenderer | null = null;

const props = defineProps<{ height?: number; width?: number }>();

onMounted(() => {
  if (rootElement.value) {
    carVisualization = new CarModelRenderer(rootElement.value, {
      width: props.width || 300,
      height: props.height || 300,
    });
    carVisualization.updatePan(store.camPan);
    carVisualization.updateTilt(store.camTilt);
    carVisualization.updateDistance(store.distance);
    carVisualization.updateServoDir(store.servoAngle);
    carVisualization.updateSpeed(store.speed);
  }
});

watch(
  () => store.distance,
  (newVal) => {
    carVisualization?.updateDistance(newVal);
  },
);

watch(
  () => store.speed,
  (newVal) => {
    carVisualization?.updateSpeed(newVal);
  },
);

watch(
  () => store.direction,
  (newVal) => {
    carVisualization?.updateDirection(newVal);
  },
);

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
