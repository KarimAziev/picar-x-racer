<template>
  <SelectField
    label="Video Quality"
    field="video_feed_url"
    v-model="store.settings.video_feed_quality"
    optionLabel="label"
    optionValue="value"
    :options="videoFeedOptions"
  />
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";

import SelectField from "@/ui/SelectField.vue";
import { numberSequence } from "@/util/cycleValue";

const videoFeedOptions = numberSequence(10, 100, 10).map((value) => ({
  value: value,
  label: `${value}`,
}));

const store = useSettingsStore();
</script>
