<template>
  <InfoBlock v-if="calibrationMode" class="calibration-info">
    <InfoItem label="Calibration" value="ON" />
    <InfoItem
      v-for="(value, field) in calibrationData"
      :key="field"
      :label="`${field}`"
      :value="`${value}`"
    />
    <InfoItem
      label="Left Motor"
      v-tooltip="'Click to toggle direction'"
      class="motor-info"
      :value="calibrationStore.data.left_motor_direction"
      @click="store.reverseLeftMotor"
    >
    </InfoItem>
    <InfoItem
      label="Right Motor"
      v-tooltip="'Click to toggle direction'"
      class="motor-info"
      :value="calibrationStore.data.right_motor_direction"
      @click="store.reverseRightMotor"
    >
    </InfoItem>

    <div class="calibration-buttons">
      <Button size="small" outlined @click="store.saveCalibration"
        >Save calibration
      </Button>
      <Button size="small" text @click="store.toggleCalibration"
        >Stop calibration</Button
      >
    </div>
    <div class="calibration-buttons">
      <Button size="small" outlined @click="store.servoTest"
        >Test servos
      </Button>
      <Button size="small" text @click="store.resetCalibration"
        >Reset calibration</Button
      >
    </div>
  </InfoBlock>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";
import { useCalibrationStore } from "@/features/settings/stores";
import InfoItem from "@/ui/InfoItem.vue";
import InfoBlock from "@/ui/InfoBlock.vue";
import { omit } from "@/util/obj";

const store = useControllerStore();
const calibrationStore = useCalibrationStore();
const calibrationMode = computed(() => store.calibrationMode);
const calibrationData = computed(() =>
  omit(
    ["left_motor_direction", "right_motor_direction"],
    calibrationStore.data,
  ),
);
</script>

<style scoped lang="scss">
.calibration-buttons {
  margin: 0.2rem 0;
}
.motor-info {
  cursor: pointer;
  transition: all 0.3s ease;
  &:hover {
    opacity: 0.7;
  }
}
</style>
