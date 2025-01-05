<template>
  <SpeedometerGauge
    :size="size"
    :segments="segments"
    :value="speed"
    :minValue="0"
    :maxValue="MAX_SPEED"
    :disabled-threshold="maxSpeed"
    :extraInfo="extraInfo"
    class="portrait:display-hidden"
  />
</template>
<script setup lang="ts">
import { computed } from "vue";
import {
  useControllerStore,
  MAX_SPEED,
  ACCELERATION,
} from "@/features/controller/store";
import SpeedometerGauge from "@/features/controller/components/SpeedometerGauge.vue";
import { speedToReal } from "@/util/speed";
import { useWindowSize } from "@/composables/useWindowSize";
import { constrain } from "@/util/constrain";

const store = useControllerStore();
const { width } = useWindowSize();

const size = computed(() => {
  const baseSize = width.value / 7;
  return constrain(255, 300, baseSize);
});

const speed = computed(() =>
  store.direction > 0 ? store.speed : -store.speed,
);

const segments = computed(() => MAX_SPEED / ACCELERATION);

const extraInfo = computed(() => `${speedToReal(speed.value)} km/h`);
const maxSpeed = computed(() => store.maxSpeed);
</script>
