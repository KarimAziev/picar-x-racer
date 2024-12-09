<template>
  <DataTable :value="files" :loading="loading" @rowReorder="onRowReorder">
    <template #header>
      <div class="flex jc-between align-items-center">
        <div class="flex gap-16">
          <SelectField
            field="settings.music.mode"
            label="Default Mode"
            class="mode-select"
            :options="musicModes"
            v-model="musicStore.player.mode"
            @update:model-value="handleUpdateMusicMode"
          />
        </div>
      </div>
    </template>
    <Column rowReorder headerStyle="width: 3rem" :reorderableColumn="false" />
    <Column class="track-col" field="track" header="Track"></Column>
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
            aria-label="Pause"
          />
          <Button
            @click="playTrack(slotProps.data.track)"
            v-else
            icon="pi pi-play-circle"
            text
            aria-label="Play"
          />
          <Button
            rounded
            v-tooltip="'Download file'"
            severity="secondary"
            text
            icon="pi pi-download"
            @click="handleDownloadFile(slotProps.data.track)"
          >
          </Button>
          <Button
            v-if="slotProps.data.removable"
            icon="pi pi-trash"
            severity="danger"
            text
            @click="handleRemove(slotProps.data.track)"
          />
        </ButtonGroup>
      </template>
    </Column>
  </DataTable>
  <FileUpload
    class="upload-btn"
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
</template>

<script setup lang="ts">
import { mediaType, FileDetail, MusicMode } from "@/features/music";
import { computed } from "vue";
import type { DataTableRowReorderEvent } from "primevue/datatable";
import type { FileUploadUploadEvent } from "primevue/fileupload";
import FileUpload from "primevue/fileupload";
import ButtonGroup from "primevue/buttongroup";
import SelectField from "@/ui/SelectField.vue";

import { secondsToReadableString } from "@/util/time";
import { startCase } from "@/util/str";
import { useMusicStore } from "@/features/music";

const apiURL = `/api/files/upload/${mediaType}`;

const musicStore = useMusicStore();
const musicModes = Object.values(MusicMode).map((value) => ({
  value,
  label: startCase(value),
}));

const files = computed(() => musicStore.data);
const loading = computed(() => musicStore.loading);

const isPlaying = (track: string) =>
  musicStore.player.track === track && musicStore.player.is_playing;

const playTrack = async (track: string) => {
  await musicStore.playTrack(track);
};

const handleUpdateMusicMode = async (mode: MusicMode) => {
  await musicStore.updateMode(mode);
};

const pauseTrack = async () => {
  await musicStore.togglePlaying();
};
const handleUpdateOrder = async (files: FileDetail[]) => {
  const tracks = files.map(({ track }) => track);
  await musicStore.updateMusicOrder(tracks);
};

const onRowReorder = async (e: DataTableRowReorderEvent) => {
  const files: FileDetail[] = e.value;
  await handleUpdateOrder(files);
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
  await handleUpdateOrder(musicStore.data);
};
</script>
<style scoped lang="scss">
:deep(.track-col) {
  max-width: 100px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  @media (min-width: 768px) {
    & {
      max-width: 120px;
    }
  }
  @media (min-width: 1200px) {
    & {
      max-width: 300px;
    }
  }
}

.mode-select {
  width: 100%;
  min-width: 200px;
}

.upload-btn {
  margin-top: 1rem;
}
</style>
