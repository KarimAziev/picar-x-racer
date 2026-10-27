<template>
  <SpeedometerGauge
    :size="size"
    :segments="segments"
    :value="speed"
    :minValue="0"
    :maxValue="maxValue"
    :disabled-threshold="maxSpeed"
    class="portrait:display-hidden"
  >
    <template #extra>
      <div class="flex flex-col justify-end items-end">
        <template v-if="encoderCalibrationRequired">
          <div>Encoder:</div>
          <span>Calibration required</span>
        </template>
        <template v-if="encoderSpeedKmh !== null">
          <div>Encoder:</div>
          <span>{{ roundToTwoDecimalPlaces(encoderSpeedKmh) }} km/h</span>
        </template>
        <template v-else-if="distanceStore.speed != null">
          <div>Ultrasonic:</div>
          <span>{{ distanceStore.speed }} km/h</span>
        </template>
        <div>Command estimate:</div>
        <span>{{ speedToReal(speed) }} km/h</span>
      </div>
    </template>
  </SpeedometerGauge>
</template>
<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore, ACCELERATION } from "@/features/controller/store";
import SpeedometerGauge from "@/features/controller/components/SpeedometerGauge.vue";
import { speedToReal } from "@/util/speed";
import { useWindowSize } from "@/composables/useWindowSize";
import { constrain } from "@/util/constrain";
import { useRobotStore, useDistanceStore } from "@/features/settings/stores";

import { useEncoderTelemetry } from "@/features/controller/composables/useEncoderTelemetry";
import { roundToTwoDecimalPlaces } from "@/util/number";

const { encoderSpeedKmh, encoderCalibrationRequired } = useEncoderTelemetry();
const store = useControllerStore();
const robotStore = useRobotStore();
const distanceStore = useDistanceStore();
const { width } = useWindowSize();

const size = computed(() => {
  const baseSize = width.value / 7;
  return constrain(255, 300, baseSize);
});

const speed = computed(() =>
  store.direction > 0 ? store.speed : -store.speed,
);

const maxValue = computed(() => robotStore.maxSpeed);
const segments = computed(() =>
  constrain(10, 15, maxValue.value / ACCELERATION),
);

const maxSpeed = computed(() => store.maxSpeed);
</script>
