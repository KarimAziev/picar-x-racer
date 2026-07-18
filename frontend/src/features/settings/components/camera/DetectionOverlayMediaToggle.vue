<template>
  <ToggleSwitchField
    v-bind="props"
    labelClassName="pb-1"
    field="include_detection_overlay_in_media"
    tooltipHelp="Whether captured photos and recorded videos should include detection boxes."
    label="Detection boxes in media"
    v-model="streamStore.data.include_detection_overlay_in_media"
    @update:model-value="updateField"
  />
</template>

<script setup lang="ts">
import { useSettingsStore, useStreamStore } from "@/features/settings/stores";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import type { Props } from "@/ui/ToggleSwitchField.vue";

import { useAsyncDebounce } from "@/composables/useDebounce";

const props =
  defineProps<
    Omit<Props, "labelClassName" | "modelValue" | "label" | "tooltip" | "field">
  >();

const settingsStore = useSettingsStore();

const streamStore = useStreamStore();

const updateField = useAsyncDebounce(async (newValue: boolean) => {
  settingsStore.data.stream.include_detection_overlay_in_media = newValue;
  streamStore.data.include_detection_overlay_in_media = newValue;
  await streamStore.updateData(streamStore.data);
}, 500);
</script>
