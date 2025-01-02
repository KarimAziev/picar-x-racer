<template>
  <ToggleSwitchField
    field="render_fps"
    layout="row-reverse"
    v-tooltip="'Whether to draw FPS on the top-right corner'"
    label="Render FPS"
    fieldClassName="flex-row-reverse gap-2.5 items-center justify-end"
    v-model="streamStore.data.render_fps"
    @update:model-value="updateRenderFPS"
  />
</template>

<script setup lang="ts">
import { useSettingsStore, useStreamStore } from "@/features/settings/stores";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";

const settingsStore = useSettingsStore();

const streamStore = useStreamStore();

const updateRenderFPS = async (newValue: boolean) => {
  settingsStore.data.stream.render_fps = newValue;
  streamStore.data.render_fps = newValue;
  await streamStore.updateData(streamStore.data);
};
</script>
