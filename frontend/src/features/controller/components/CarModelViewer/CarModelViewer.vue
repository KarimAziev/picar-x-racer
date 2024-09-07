<template>
  <div ref="rootElement" class="wrapper" :class="class" />
</template>

<script setup lang="ts">
import * as THREE from "three";
import { ref, onMounted, onUnmounted, watch } from "vue";
import { CarModelRenderer } from "@/features/controller/components/CarModelViewer/CarModelRenderer";
import { useControllerStore } from "@/features/controller/store";
import { useElementSize } from "@/composables/useElementSize";
import { useDistanceStore } from "@/features/settings/stores";
import { isNumber } from "@/util/guards";

const props = defineProps<{
  class?: string;
  zoom?: number;
  rotationY?: number;
  rotationX?: number;
  cameraPosition?: [x: number, y: number, z: number];
}>();

const store = useControllerStore();
const distanceStore = useDistanceStore();
const rootElement = ref<HTMLElement | null>(null);
const parentSize = useElementSize(rootElement);
let carVisualization: CarModelRenderer | null = null;

onMounted(() => {
  if (rootElement.value) {
    carVisualization = new CarModelRenderer(rootElement.value, {
      width: parentSize.width,
      height: parentSize.height,
      bodyLength: 1.5,
    });
    carVisualization.updatePan(store.camPan);
    carVisualization.updateTilt(store.camTilt);
    carVisualization.updateDistance(distanceStore.distance);
    carVisualization.updateServoDir(store.servoAngle);
    carVisualization.updateSpeed(store.speed);
    if (props.zoom) {
      carVisualization.camera.zoom = props.zoom;
    }
    if (props.cameraPosition) {
      carVisualization.camera.position.set(...props.cameraPosition);
    }
    if (isNumber(props.rotationY)) {
      carVisualization.cameraObject.rotation.y = THREE.MathUtils.degToRad(
        props.rotationY,
      );
    }
    if (isNumber(props.rotationX)) {
      carVisualization.cameraObject.rotation.x = THREE.MathUtils.degToRad(
        props.rotationX,
      );
    }
  }
});

watch(
  () => ({ ...parentSize }),
  (newVal) => {
    carVisualization?.setSize(newVal.width, newVal.height);
  },
);

watch(
  () => distanceStore.distance,
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
<style scoped lang="scss">
.wrapper {
  width: 100%;
  height: 100%;
}
</style>
