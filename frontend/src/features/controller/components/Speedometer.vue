<template>
  <div class="speedometer-wrapper">
    <SpeedometerGauge
      :segments="10"
      :value="store.speed"
      :minValue="0"
      :maxValue="100"
    />
  </div>
</template>
<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import SpeedometerGauge from "@/features/controller/components/SpeedometerGauge.vue";

const store = useControllerStore();
</script>

<style scoped></style>
