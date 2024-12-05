<template>
  <VideoDeviceSelect />
  <SelectField
    label="Video Quality"
    field="video_feed_quality"
    v-model="streamStore.data.quality"
    optionLabel="label"
    optionValue="value"
    :options="videoFeedOptions"
    :loading="streamStore.loading"
    @update:model-value="updateStreamParams"
  />
  <SelectField
    optionLabel="label"
    optionValue="value"
    label="Enhance Mode"
    field="video_feed_enhance_mode"
    v-model="streamStore.data.enhance_mode"
    :loading="streamStore.loading"
    :options="enhancers"
    @update:model-value="updateStreamParams"
  />
</template>

<script setup lang="ts">
import { onMounted, computed } from "vue";

import { useSettingsStore, useStreamStore } from "@/features/settings/stores";

import SelectField from "@/ui/SelectField.vue";
import { numberSequence } from "@/util/cycleValue";
import { objectKeysToOptions } from "@/features/settings/util";
import VideoDeviceSelect from "@/features/settings/components/VideoDeviceSelect.vue";
import { useAsyncDebounce } from "@/composables/useDebounce";

const store = useSettingsStore();

const streamStore = useStreamStore();

const enhancers = computed(() => [
  ...objectKeysToOptions(streamStore.enhancers),
  { label: "None", value: null },
]);

const updateStreamParams = useAsyncDebounce(async () => {
  store.data.stream = streamStore.data;
  await streamStore.updateData(streamStore.data);
}, 2000);

const videoFeedOptions = numberSequence(10, 100, 10).map((value) => ({
  value: value,
  label: `${value}`,
}));

onMounted(async () => {
  if (!streamStore.enhancers.length) {
    streamStore.fetchEnhancers();
  }
});
</script>
