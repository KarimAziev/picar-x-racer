<template>
  <div class="info">
    <InfoItem label="Camera Tilt:" :value="store.camTilt" />
    <InfoItem label="Camera Pan:" :value="store.camPan" />
    <InfoItem label="Servo Direction:" :value="store.servoAngle" />
    <InfoItem label="Distance:" :value="store.distance" />
    <InfoItem label="Max Speed:" :value="store.maxSpeed" />
  </div>
</template>

<script setup lang="ts">
import { useControllerStore } from "@/stores/controller";
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
