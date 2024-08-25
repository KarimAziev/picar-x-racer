<template>
  <div v-if="store.avoidObstacles" class="info">
    <InfoItem label="Autopilot is on" />
  </div>
  <div class="info" v-else>
    <InfoItem label="Camera Tilt" :value="store.camTilt" value-suffix="°" />
    <InfoItem label="Camera Pan" :value="store.camPan" value-suffix="°" />
    <InfoItem
      label="Servo Direction"
      :value="store.servoAngle"
      value-suffix="°"
    />
    <InfoItem label="Max Speed" :value="store.maxSpeed" />
  </div>
</template>

<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import InfoItem from "@/ui/InfoItem.vue";

const store = useControllerStore();
</script>

<style scoped lang="scss">
.info {
  text-transform: uppercase;
  display: flex;
  width: 350px;
  flex-direction: column;
  padding: 1rem;
}
</style>
