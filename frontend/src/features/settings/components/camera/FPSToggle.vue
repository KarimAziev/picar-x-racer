<template>
  <ToggleSwitchField
    label="Render FPS"
    layout="row-reverse"
    :pt="{ input: { id: 'render_fps' } }"
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
