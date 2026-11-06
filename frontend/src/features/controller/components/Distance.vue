<template>
  <div
    class="flex justify-between gap-2 text-left items-center"
    v-if="isLoaded"
  >
    <span class="flex flex-wrap gap-2 items-center">
      <span class="font-bold">Ultrasonic distance</span>

      <ButtonIcon
        :disabled="avoidObstacles"
        v-tooltip.left="
          avoidObstacles
            ? 'Disabled while ultrasonic obstacle avoidance is active'
            : 'Toggle automatic ultrasonic measurements'
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

const distance = computed(
  () => `${(distanceStore.distance || 0).toFixed(2)}cm`,
);
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
