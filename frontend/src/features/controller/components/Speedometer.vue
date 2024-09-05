<template>
  <SpeedometerGauge
    :segments="10"
    :value="speed"
    :minValue="0"
    :maxValue="100"
  />
</template>
<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import SpeedometerGauge from "@/features/controller/components/SpeedometerGauge.vue";
import { computed } from "vue";

const store = useControllerStore();
const speed = computed(() =>
  store.direction > 0 ? store.speed : -store.speed,
);
</script>

<style scoped></style>
