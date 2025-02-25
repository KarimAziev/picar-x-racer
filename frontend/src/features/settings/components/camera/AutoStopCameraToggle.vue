<template>
  <ToggleSwitchField
    field="auto_stop_camera_on_disconnect"
    layout="row-reverse"
    tooltip="Whether the camera should be auto-stopped when the last websocket client disconnects."
    label="Auto stop camera"
    fieldClassName="flex-row-reverse gap-2.5 items-center justify-end"
    v-model="streamStore.data.auto_stop_camera_on_disconnect"
    @update:model-value="updateField"
  />
</template>

<script setup lang="ts">
import { useSettingsStore, useStreamStore } from "@/features/settings/stores";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";

const settingsStore = useSettingsStore();

const streamStore = useStreamStore();

const updateField = async (newValue: boolean) => {
  settingsStore.data.stream.auto_stop_camera_on_disconnect = newValue;
  streamStore.data.auto_stop_camera_on_disconnect = newValue;
  await streamStore.updateData(streamStore.data);
};
</script>
