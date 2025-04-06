<template>
  <SelectField
    :class="class"
    label="Video Quality"
    field="video_feed_quality"
    v-model="streamStore.data.quality"
    tooltipHelp="Quality compression level for frames"
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

defineProps<{ class?: string }>();

const updateStreamParams = useAsyncDebounce(async () => {
  settingsStore.data.stream = streamStore.data;
  await streamStore.updateData(streamStore.data);
}, 500);
</script>
