<template>
  <div class="flex justify-between text-left" v-if="isLoaded">
    <button
      :disabled="avoidObstacles"
      v-tooltip="'Click to toggle auto distance measure'"
      @click="handleToggle"
      class="font-bold text-inherit cursor-pointer p-0 border-none bg-transparent transition-opacity duration-300 ease-in-out hover:opacity-70 focus:outline-none"
    >
      {{ distanceLabel }}:
    </button>
    &nbsp;
    <samp>{{ distance }}</samp>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore, useDistanceStore } from "@/features/settings/stores";
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";

const settingsStore = useSettingsStore();
const distanceStore = useDistanceStore();

const distance = computed(() => `${distanceStore.distance.toFixed(2)}cm`);
const isLoaded = computed(() => settingsStore.loaded);
const controllerStore = useControllerStore();
const avoidObstacles = computed(() => controllerStore.avoidObstacles);
const isAutoMeasureMode = computed(
  () =>
    settingsStore.loaded && settingsStore.data.robot.auto_measure_distance_mode,
);

const handleToggle = () => {
  controllerStore.toggleAutoMeasureDistanceMode();
};

const distanceLabel = computed(() =>
  isAutoMeasureMode.value ? "DISTANCE ON" : "DISTANCE OFF",
);
</script>
