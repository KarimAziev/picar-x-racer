<template>
  <SpeedometerGauge
    :segments="10"
    :value="speed"
    :minValue="0"
    :maxValue="100"
    :disabled-threshold="maxSpeed"
    :extraInfo="extraInfo"
    class="speedometer"
  />
</template>
<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";
import SpeedometerGauge from "@/features/controller/components/SpeedometerGauge.vue";
import { speedToReal } from "@/util/speed";

const store = useControllerStore();
const speed = computed(() =>
  store.direction > 0 ? store.speed : -store.speed,
);

const extraInfo = computed(() => `${speedToReal(speed.value)} km/h`);
const maxSpeed = computed(() => store.maxSpeed);
</script>
<style scoped lang="scss">
.speedometer {
  @media screen and (max-width: 1200px) and (orientation: portrait) {
    display: none;
  }
  @media (max-width: 1200px) {
    transform: scale(0.5);
    translate: 25% 25%;
  }

  @media (max-width: 1440px) {
    transform: scale(0.7);
    translate: 6% 7%;
  }
}
</style>
