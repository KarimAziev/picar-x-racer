<template>
  <div class="info">
    <InfoItem label="Camera Tilt:" :value="store.camTilt" value-suffix="°" />
    <InfoItem label="Camera Pan:" :value="store.camPan" value-suffix="°" />
    <InfoItem
      label="Servo Direction:"
      :value="store.servoAngle"
      value-suffix="°"
    />
    <InfoItem label="Distance:" :value="store.distance" />
    <InfoItem label="Max Speed:" :value="store.maxSpeed" />
  </div>
</template>

<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import InfoItem from "@/ui/InfoItem.vue";

const store = useControllerStore();
</script>
<style scoped lang="scss">
.info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  white-space: nowrap;
}
</style>
