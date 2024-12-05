<template>
  <Field label="Render FPS" layout="row-reverse">
    <ToggleSwitch
      :pt="{ input: { id: 'render_fps' } }"
      v-model="streamStore.data.render_fps"
      @update:model-value="updateRenderFPS"
    />
  </Field>
</template>

<script setup lang="ts">
import ToggleSwitch from "primevue/toggleswitch";
import { useSettingsStore, useStreamStore } from "@/features/settings/stores";
import Field from "@/ui/Field.vue";

const settingsStore = useSettingsStore();

const streamStore = useStreamStore();

const updateRenderFPS = async (newValue: boolean) => {
  settingsStore.data.stream.render_fps = newValue;
  streamStore.data.render_fps = newValue;
  await streamStore.updateData(streamStore.data);
};
</script>
