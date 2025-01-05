<template>
  <SelectField
    label="Video Quality"
    field="video_feed_quality"
    v-model="streamStore.data.quality"
    tooltip="Quality compression level for frames (%s)"
    optionLabel="label"
    optionValue="value"
    :options="videoQualityOptions"
    :loading="streamStore.loading"
    @update:model-value="updateStreamParams"
  />
</template>

<script setup lang="ts">
import SelectField from "@/ui/SelectField.vue";
import { useSettingsStore, useStreamStore } from "@/features/settings/stores";
import { videoQualityOptions } from "@/features/settings/config";
import { useAsyncDebounce } from "@/composables/useDebounce";

const settingsStore = useSettingsStore();
const streamStore = useStreamStore();

const updateStreamParams = useAsyncDebounce(async () => {
  settingsStore.data.stream = streamStore.data;
  await streamStore.updateData(streamStore.data);
}, 2000);
</script>
