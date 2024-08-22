<template>
  <main>
    <BatteryIndicator />
    <CarController />
  </main>
</template>

<script setup lang="ts">
import CarController from "@/features/controller/CarController.vue";
import BatteryIndicator from "@/features/settings/components/BatteryIndicator.vue";
</script>
