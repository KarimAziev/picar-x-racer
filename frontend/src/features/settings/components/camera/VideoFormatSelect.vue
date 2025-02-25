<template>
  <SelectField
    label="Video format"
    field="format"
    v-model="streamStore.data.format"
    tooltip="This setting defines the container and codec used when encoding video streams."
    optionLabel="label"
    optionValue="value"
    :options="videoEncodeFormatOptions"
    :loading="streamStore.loading"
    @update:model-value="updateStreamParams"
  />
</template>

<script setup lang="ts">
import SelectField from "@/ui/SelectField.vue";
import { useSettingsStore, useStreamStore } from "@/features/settings/stores";
import { videoEncodeFormatOptions } from "@/features/settings/config";
import { useAsyncDebounce } from "@/composables/useDebounce";

const settingsStore = useSettingsStore();
const streamStore = useStreamStore();

const updateStreamParams = useAsyncDebounce(async () => {
  settingsStore.data.stream = streamStore.data;
  await streamStore.updateData(streamStore.data);
}, 500);
</script>
