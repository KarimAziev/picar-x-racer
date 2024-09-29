<template>
  <SelectField
    label="Video Quality"
    field="video_feed_quality"
    v-model="store.settings.video_feed_quality"
    optionLabel="label"
    optionValue="value"
    :options="videoFeedOptions"
  />
  <SelectField
    label="Object Detection Mode"
    optionLabel="label"
    optionValue="value"
    field="video_feed_detect_mode"
    v-model="store.settings.video_feed_detect_mode"
    :options="detectors"
  />
  <NumberField
    inputId="video_feed_fps"
    label="Object detection confidence"
    v-model="store.settings.video_feed_confidence"
    :min="0.1"
    :max="1.0"
    :step="0.1"
  />
  <SelectField
    optionLabel="label"
    optionValue="value"
    label="Enhance Mode"
    field="video_feed_enhance_mode"
    v-model="store.settings.video_feed_enhance_mode"
    :options="enhancers"
  />

  <NumberField
    inputId="video_feed_fps"
    label="FPS"
    v-model="store.settings.video_feed_fps"
    :min="10"
    :max="80"
    :step="10"
  />
</template>

<script setup lang="ts">
import { onMounted, computed, watch } from "vue";
import { useSettingsStore, useCameraStore } from "@/features/settings/stores";

import SelectField from "@/ui/SelectField.vue";
import { numberSequence } from "@/util/cycleValue";
import NumberField from "@/ui/NumberField.vue";
import { objectKeysToOptions } from "@/features/settings/util";

const detectors = computed(() => [
  ...objectKeysToOptions(camStore.detectors),
  { label: "None", value: null },
]);

const enhancers = computed(() => [
  ...objectKeysToOptions(camStore.enhancers),
  { label: "None", value: null },
]);

const videoFeedOptions = numberSequence(10, 100, 10).map((value) => ({
  value: value,
  label: `${value}`,
}));

const store = useSettingsStore();
const camStore = useCameraStore();

onMounted(async () => {
  if (!camStore.detectors.length) {
    await camStore.fetchConfig();
  }
});

watch(
  () => store.settings.video_feed_fps,
  (newVal) => {
    camStore.updateCameraParams({ video_feed_fps: newVal });
  },
);
watch(
  () => store.settings.video_feed_fps,
  (newVal) => {
    camStore.updateCameraParams({ video_feed_fps: newVal });
  },
);

watch(
  () => store.settings.video_feed_enhance_mode,
  (newVal) => {
    camStore.updateCameraParams({ video_feed_enhance_mode: newVal });
  },
);
watch(
  () => store.settings.video_feed_detect_mode,
  (newVal) => {
    camStore.updateCameraParams({ video_feed_detect_mode: newVal });
  },
);

watch(
  () => store.settings.video_feed_quality,
  (newVal) => {
    camStore.updateCameraParams({ video_feed_quality: newVal });
  },
);
</script>
