<template>
  <ToggleSwitchField
    v-bind="props"
    labelClassName="pb-1"
    field="auto_stop_camera_on_disconnect"
    tooltipHelp="Whether the camera should be auto-stopped when the last websocket client disconnects."
    label="Auto stop camera"
    v-model="streamStore.data.auto_stop_camera_on_disconnect"
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
  settingsStore.data.stream.auto_stop_camera_on_disconnect = newValue;
  streamStore.data.auto_stop_camera_on_disconnect = newValue;
  await streamStore.updateData(streamStore.data);
}, 500);
</script>
