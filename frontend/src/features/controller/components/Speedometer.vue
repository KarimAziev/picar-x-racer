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
        <div v-if="distanceStore.speed">Ultrasonic:</div>
        <span v-if="distanceStore.speed">{{ distanceStore.speed }} km/h</span>
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
