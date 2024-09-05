<template>
  <div v-if="avoidObstacles" class="info">
    <InfoItem label="Autopilot is on" />
  </div>
  <div class="info" v-else>
    <InfoItem
      v-if="!calibrationMode"
      label="Camera Tilt"
      :value="camTilt"
      value-suffix="°"
    />
    <InfoItem
      v-if="!calibrationMode"
      label="Camera Pan"
      :value="camPan"
      value-suffix="°"
    />
    <InfoItem
      v-if="!calibrationMode"
      label="Servo Direction"
      :value="servoAngle"
      value-suffix="°"
    />
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
      <Button size="small" text @click="store.toggleCalibration"
        >Stop calibration</Button
      >
    </div>
    <div v-if="calibrationMode" class="calibration-buttons">
      <Button size="small" outlined @click="store.servoTest"
        >Test servos
      </Button>
      <Button size="small" text @click="store.resetCalibration"
        >Reset servos</Button
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
