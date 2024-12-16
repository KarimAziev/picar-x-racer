<template>
  <div ref="rootElement" class="wrapper" :class="class" />
</template>

<script setup lang="ts">
import * as THREE from "three";
import { onBeforeUnmount, ref, onMounted, watch } from "vue";
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

const carVisualization = ref<CarModelRenderer | null>(null);

onMounted(() => {
  if (!rootElement.value) {
    return;
  }
  carVisualization.value = new CarModelRenderer(rootElement.value, {
    width: parentSize.width,
    height: parentSize.height,
    bodyLength: 1.5,
  });

  carVisualization.value.updatePan(store.camPan);
  carVisualization.value.updateTilt(store.camTilt);
  carVisualization.value.updateDistance(distanceStore.distance);
  carVisualization.value.updateServoDir(store.servoAngle);
  carVisualization.value.updateSpeed(store.speed);
  if (props.zoom) {
    carVisualization.value.camera.zoom = props.zoom;
  }
  if (props.cameraPosition) {
    carVisualization.value.camera.position.set(...props.cameraPosition);
  }
  if (isNumber(props.rotationY)) {
    carVisualization.value.cameraObject.rotation.y = THREE.MathUtils.degToRad(
      props.rotationY,
    );
  }
  if (isNumber(props.rotationX)) {
    carVisualization.value.cameraObject.rotation.x = THREE.MathUtils.degToRad(
      props.rotationX,
    );
  }
});

watch(
  () => ({ ...parentSize }),
  (newVal) => {
    carVisualization.value?.setSize(newVal.width, newVal.height);
  },
);

watch(
  () => distanceStore.distance,
  (newVal) => {
    carVisualization.value?.updateDistance(newVal);
  },
);

watch(
  () => store.speed,
  (newVal) => {
    carVisualization.value?.updateSpeed(newVal);
  },
);

watch(
  () => store.direction,
  (newVal) => {
    carVisualization.value?.updateDirection(newVal);
  },
);

watch(
  () => store.camPan,
  (newVal) => {
    carVisualization.value?.updatePan(newVal);
  },
);

watch(
  () => store.camTilt,
  (newVal) => {
    carVisualization.value?.updateTilt(newVal);
  },
);

watch(
  () => store.servoAngle,
  (newVal) => {
    carVisualization.value?.updateServoDir(newVal);
  },
);

onBeforeUnmount(() => {
  carVisualization.value?.dispose();
  carVisualization.value = null;
});
</script>
<style scoped lang="scss">
.wrapper {
  width: 100%;
  height: 100%;
}
</style>
