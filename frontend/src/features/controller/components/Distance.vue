<template>
  <div class="flex justify-between text-left items-center" v-if="isLoaded">
    <span clas="flex items-center">
      <span class="font-bold">Distance</span> &nbsp;

      <ButtonIcon
        :disabled="avoidObstacles"
        v-tooltip.left="
          avoidObstacles
            ? 'Disabled while avoid obstacles mode is active'
            : 'Toggle auto distance measuring'
        "
        @click="handleToggle"
        class="px-2 py-0 border border-current rounded-md"
      >
        {{ distanceLabel }}
      </ButtonIcon>
    </span>

    <samp>{{ distance }}</samp>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore, useDistanceStore } from "@/features/settings/stores";
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";
import ButtonIcon from "@/ui/ButtonIcon.vue";

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

const distanceLabel = computed(() => (isAutoMeasureMode.value ? "ON" : "OFF"));
</script>
