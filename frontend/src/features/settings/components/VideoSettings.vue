<template>
  <VideoDeviceSelect />
  <SelectField
    label="Video Quality"
    field="video_feed_quality"
    v-model="store.settings.video_feed_quality"
    optionLabel="label"
    optionValue="value"
    :options="videoFeedOptions"
    :loading="camStore.loadingData.video_feed_quality"
  />
  <ModelSelect />
  <NumberField
    inputId="video_feed_fps"
    label="Object detection confidence"
    v-model="store.settings.video_feed_confidence"
    :loading="camStore.loadingData.video_feed_confidence"
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
    :loading="camStore.loadingData.video_feed_enhance_mode"
    :options="enhancers"
  />
</template>

<script setup lang="ts">
import { onMounted, computed, watch } from "vue";

import { useSettingsStore, useCameraStore } from "@/features/settings/stores";

import SelectField from "@/ui/SelectField.vue";
import { numberSequence } from "@/util/cycleValue";
import NumberField from "@/ui/NumberField.vue";
import { objectKeysToOptions } from "@/features/settings/util";
import VideoDeviceSelect from "@/features/settings/components/VideoDeviceSelect.vue";
import { roundNumber } from "@/util/number";
import { isNumber } from "@/util/guards";
import ModelSelect from "@/features/settings/components/ModelSelect.vue";

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
  if (!camStore.enhancers.length) {
    camStore.fetchEnhancers();
  }
});

watch(
  () => store.settings.video_feed_confidence,
  (newVal) => {
    camStore.updateCameraParams({
      video_feed_confidence: isNumber(newVal) ? roundNumber(newVal, 1) : newVal,
    });
  },
);

watch(
  () => store.settings.video_feed_enhance_mode,
  (newVal) => {
    camStore.updateCameraParams({ video_feed_enhance_mode: newVal });
  },
);

watch(
  () => store.settings.video_feed_quality,
  (newVal) => {
    camStore.updateCameraParams({ video_feed_quality: newVal });
  },
);
</script>
