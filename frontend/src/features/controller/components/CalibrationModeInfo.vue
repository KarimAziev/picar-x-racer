<template>
  <InfoBlock v-if="calibrationMode" class="calibration-info">
    <InfoItem label="Calibration" value="ON" />
    <InfoItem
      v-for="(value, field) in calibrationData"
      :key="field"
      :label="`${field}`"
      :value="`${value}`"
    />
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
        >Reset servos</Button
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

const store = useControllerStore();
const calibrationStore = useCalibrationStore();
const calibrationMode = computed(() => store.calibrationMode);
const calibrationData = computed(() => calibrationStore.data);
</script>

<style scoped lang="scss">
.calibration-buttons {
  margin: 1rem 0;
}
</style>
