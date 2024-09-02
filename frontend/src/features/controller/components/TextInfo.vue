<template>
  <div v-if="avoidObstacles" class="info">
    <InfoItem label="Autopilot is on" />
  </div>
  <div class="info" v-else>
    <InfoItem label="Camera Tilt" :value="camTilt" value-suffix="°" />
    <InfoItem label="Camera Pan" :value="camPan" value-suffix="°" />
    <InfoItem label="Servo Direction" :value="servoAngle" value-suffix="°" />
    <InfoItem label="Distance" :value="distance.toFixed(2)" value-suffix="cm" />
    <InfoItem label="Max Speed" :value="maxSpeed" />
    <InfoItem
      v-if="calibrationMode"
      v-for="(value, field) in calibrationStore.data"
      :key="field"
      class="field"
      :label="`${field}`"
      :value="`${value}`"
    />
    <div v-if="calibrationMode" class="calibration-buttons">
      <Button size="small" outlined @click="store.saveCalibration"
        >Save calibration
      </Button>
      <Button size="small" text @click="store.resetCalibration"
        >Reset calibration</Button
      >
    </div>
    <div v-if="calibrationMode" class="calibration-buttons">
      <Button size="small" plain @click="store.toggleCalibration"
        >Stop calibration</Button
      >
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";
import { useCalibrationStore } from "@/features/settings/stores";
import InfoItem from "@/ui/InfoItem.vue";

const store = useControllerStore();
const calibrationStore = useCalibrationStore();
const avoidObstacles = computed(() => store.avoidObstacles);
const calibrationMode = computed(() => store.calibrationMode);
const camPan = computed(() => store.camPan);
const camTilt = computed(() => store.camTilt);
const servoAngle = computed(() => store.servoAngle);
const distance = computed(() => store.distance);
const maxSpeed = computed(() => store.maxSpeed);
</script>

<style scoped lang="scss">
.info {
  text-transform: uppercase;
  display: flex;
  width: 350px;
  flex-direction: column;
  padding: 1rem;
}
.calibration-buttons {
  margin: 1rem 0;
}
</style>
