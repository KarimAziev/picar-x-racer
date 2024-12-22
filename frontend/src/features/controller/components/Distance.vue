<template>
  <div class="flex jc-between distance" v-if="isLoaded">
    <button
      :disabled="avoidObstacles"
      v-tooltip="'Click to toggle auto distance measure'"
      @click="handleToggle"
      class="btn bold"
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

<style scoped lang="scss">
.distance {
  text-align: left;
  color: var(--color-text);

  .btn {
    font-size: inherit;
    font-family: var(--font-family);
    cursor: pointer;
    padding: 0;
    color: var(--color-text);
    border: none;
    background-color: transparent;
    outline: none;
    transition: all 0.3s ease;
    &:hover {
      opacity: 0.7;
    }
  }
}
</style>
