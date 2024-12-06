<template>
  <SelectField
    optionLabel="label"
    optionValue="value"
    label="Enhance Mode"
    field="video_feed_enhance_mode"
    placeholder="Video Effect"
    v-model="streamStore.data.enhance_mode"
    :loading="streamStore.loading"
    :options="enhancers"
    @update:model-value="updateStreamParams"
  />
</template>

<script setup lang="ts">
import { onMounted, computed } from "vue";
import SelectField from "@/ui/SelectField.vue";
import { useSettingsStore, useStreamStore } from "@/features/settings/stores";
import { objectKeysToOptions } from "@/features/settings/util";
import { useAsyncDebounce } from "@/composables/useDebounce";

const settingsStore = useSettingsStore();
const streamStore = useStreamStore();

const enhancers = computed(() => [
  ...objectKeysToOptions(streamStore.enhancers),
  { label: "None", value: null },
]);

const updateStreamParams = useAsyncDebounce(async () => {
  settingsStore.data.stream = streamStore.data;
  await streamStore.updateData(streamStore.data);
}, 2000);

onMounted(async () => {
  if (!streamStore.enhancers.length) {
    await streamStore.fetchEnhancers();
  }
});
</script>
