<template>
  <div class="info">
    <InfoItem label="Camera Tilt" :value="store.camTilt" value-suffix="°" />
    <InfoItem label="Camera Pan" :value="store.camPan" value-suffix="°" />
    <InfoItem
      label="Servo Direction"
      :value="store.servoAngle"
      value-suffix="°"
    />
    <InfoItem label="Max Speed" :value="store.maxSpeed" />
    <InfoItem
      label="Distance"
      :value="distance"
      :value-suffix="isNumber(store.distance) ? ' sm' : ''"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";
import InfoItem from "@/ui/InfoItem.vue";
import { isNumber } from "@/util/guards";

const store = useControllerStore();

const distance = computed(() =>
  isNumber(store.distance) ? store.distance.toFixed(2) : store.distance,
);
</script>

<style scoped lang="scss">
.info {
  text-transform: uppercase;
  display: flex;
  width: 350px;
  flex-direction: column;
}
</style>
