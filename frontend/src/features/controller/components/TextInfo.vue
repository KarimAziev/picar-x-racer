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
    <InfoItem label="Battery Voltage" :value="batteryVoltage" />
    <InfoItem
      label="Distance"
      :value="distance"
      :value-suffix="isNumber(store.distance) ? 'sm' : ''"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";
import InfoItem from "@/ui/InfoItem.vue";
import { isNumber } from "@/util/guards";

const FULLY_CHARGED_VOLTAGE = 8.4;
const distance = computed(() =>
  isNumber(store.distance) ? store.distance.toFixed(2) : store.distance,
);

const batteryVoltage = computed(() =>
  isNumber(store.batteryVoltage)
    ? `${store.batteryVoltage.toFixed(2)}V of ${FULLY_CHARGED_VOLTAGE.toFixed(2)}V`
    : store.batteryVoltage,
);

const store = useControllerStore();
</script>
<style scoped lang="scss">
.info {
  display: flex;
  width: 350px;
  flex-direction: column;
  gap: 10px;
  text-transform: uppercase;
}
</style>
