<template>
  <Panel :toggleable="toggleable" :header="header" :collapsed="collapsed">
    <DataTable :value="files" :loading="loading">
      <template #header>
        <div class="flex justify-content-between align-items-center">
          <div class="flex gap-4">
            <SelectField
              field="default_music"
              label="Default Track"
              :options="files"
              optionLabel="track"
              optionValue="track"
              v-model="settingsStore.settings.default_music"
            />
          </div>
        </div>
      </template>

      <Column field="track" header="Track"></Column>
      <Column field="duration" header="Duration">
        <template #body="slotProps">
          {{ secondsToReadableString(slotProps.data.duration) }}
        </template>
      </Column>

      <Column :exportable="false" header="Actions">
        <template #body="slotProps">
          <ButtonGroup>
            <Button
              v-if="isPlaying(slotProps.data.track)"
              @click="pauseTrack"
              icon="pi pi-pause"
              text
              raised
              rounded
              aria-label="Pause"
            />
            <Button
              @click="playTrack(slotProps.data.track)"
              v-else
              icon="pi pi-play-circle"
              text
              raised
              rounded
              aria-label="Play"
            />
            <Button
              rounded
              v-tooltip="'Download file'"
              severity="secondary"
              text
              raised
              icon="pi pi-download"
              @click="handleDownloadFile(slotProps.data.track)"
            >
            </Button>
            <Button
              v-if="slotProps.data.removable"
              icon="pi pi-trash"
              outlined
              rounded
              severity="danger"
              text
              raised
              @click="handleRemove(slotProps.data.track)"
            />
          </ButtonGroup>
        </template>
      </Column>
    </DataTable>
    <FileUpload
      :auto="true"
      :disabled="loading"
      mode="basic"
      size="small"
      name="file"
      @upload="onUpload($event)"
      chooseLabel="Add"
      :url="apiURL"
      :multiple="false"
      accept="audio/*"
    >
    </FileUpload>
  </Panel>
</template>

<script setup lang="ts">
import { useStore, mediaType } from "@/features/settings/stores/music";
import { computed } from "vue";
import { default as FileUpload } from "primevue/fileupload";
import Panel from "primevue/panel";

import type { FileUploadUploadEvent } from "primevue/fileupload";
import ButtonGroup from "primevue/buttongroup";
import { secondsToReadableString } from "@/util/time";
import SelectField from "@/ui/SelectField.vue";
import { useSettingsStore } from "@/features/settings/stores";

const apiURL = `/api/upload/${mediaType}`;

const settingsStore = useSettingsStore();
const musicStore = useStore();

const files = computed(() => musicStore.data);
const loading = computed(() => musicStore.loading);

const isPlaying = (track: string) =>
  musicStore.track === track && musicStore.playing;

const playTrack = (track: string) => {
  if (musicStore.track === track) {
    musicStore.resumeMusic();
  } else {
    musicStore.playMusic(track, true, 0);
  }
};

const pauseTrack = () => {
  musicStore.pauseMusic();
};

const handleRemove = async (track: string) => {
  await musicStore.removeFile(track);
  await musicStore.fetchData();
};

const handleDownloadFile = (track: string) => {
  musicStore.downloadFile(track);
};

defineProps<{
  header?: string;
  toggleable?: boolean;
  collapsed?: boolean;
}>();

const onUpload = async (_event: FileUploadUploadEvent) => {
  await musicStore.fetchData();
};
</script>
