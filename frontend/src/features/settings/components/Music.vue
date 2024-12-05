<template>
  <Panel :toggleable="toggleable" :header="header" :collapsed="collapsed">
    <DataTable :value="files" :loading="loading" @rowReorder="onRowReorder">
      <template #header>
        <div class="flex justify-content-between align-items-center">
          <div class="flex gap-4">
            <SelectField
              field="settings.music.mode"
              label="Default Mode"
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
import {
  mediaType,
  FileDetail,
  MusicMode,
} from "@/features/settings/stores/music";
import { computed } from "vue";
import type { DataTableRowReorderEvent } from "primevue/datatable";
import type { FileUploadUploadEvent } from "primevue/fileupload";
import Panel from "@/ui/Panel.vue";
import FileUpload from "primevue/fileupload";
import ButtonGroup from "primevue/buttongroup";
import SelectField from "@/ui/SelectField.vue";
import { useMusicStore } from "@/features/settings/stores";
import { secondsToReadableString } from "@/util/time";
import { startCase } from "@/util/str";

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
.flex {
  display: flex;
}
.justify-content-between {
  justify-content: space-between;
}
.align-items-center {
  align-items: center;
}
.gap-4 {
  gap: 1rem;
}
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
</style>
