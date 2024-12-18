<template>
  <Button
    :class="className"
    class="opacity-hover"
    @click="handleToggle"
    icon="pi pi-video"
    text
    aria-label="record-video"
    v-tooltip="'Record video'"
  />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useStreamStore, useSettingsStore } from "@/features/settings/stores";

const streamStore = useStreamStore();
const settingsStore = useSettingsStore();

const isRecording = computed(() => streamStore.data.video_record);

const className = computed(
  () => `${isRecording.value ? "blink" : "opacity-hover"}`,
);

const handleToggle = async () => {
  await streamStore.toggleRecording(
    settingsStore.data.general.auto_download_video,
  );
};
</script>
