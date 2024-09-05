<template>
  <div class="distance">
    <button @click="handleToggle" text class="btn">{{ distanceLabel }}:</button>
    &nbsp;
    <samp>{{ distance }}</samp>
  </div>
</template>

<script setup lang="ts">
import {
  useSettingsStore,
  usePopupStore,
  useDistanceStore,
} from "@/features/settings/stores";
import { onMounted } from "vue";
import { computed, ref } from "vue";
const interval = 100;
const intervalId = ref<NodeJS.Timeout>();
const popupStore = usePopupStore();

const settingsStore = useSettingsStore();
const distanceStore = useDistanceStore();
const distance = computed(() => `${distanceStore.distance.toFixed(2)}cm`);
const isPopupOpen = computed(() => popupStore.isOpen);
const isAutoMeasureMode = computed(
  () => settingsStore.settings.auto_measure_distance_mode,
);

const fetchAndScheduleNext = async () => {
  if (intervalId.value) {
    clearInterval(intervalId.value);
  }
  if (isAutoMeasureMode.value && !isPopupOpen.value) {
    await distanceStore.fetchDistance();
  }
  intervalId.value = setInterval(fetchAndScheduleNext, interval);
};

const handleToggle = () => {
  settingsStore.toggleSettingsProp("auto_measure_distance_mode");
};

const distanceLabel = computed(() =>
  isAutoMeasureMode.value ? "AUTO DISTANCE ON" : "AUTO DISTANCE OFF",
);

onMounted(fetchAndScheduleNext);
</script>

<style scoped lang="scss">
.distance {
  text-align: left;
  color: var(--color-text);

  .btn {
    font-size: inherit;
    font-family: var(--font-family-settings);
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
