<template>
  <Panel :toggleable="toggleable" :header="header" :collapsed="collapsed">
    <DataTable :value="files" :loading="loading" @rowReorder="onRowReorder">
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
  useStore,
  mediaType,
  FileDetail,
} from "@/features/settings/stores/music";
import { computed } from "vue";
import FileUpload from "primevue/fileupload";
import type { DataTableRowReorderEvent } from "primevue/datatable";
import Panel from "@/ui/Panel.vue";

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

const onRowReorder = async (e: DataTableRowReorderEvent) => {
  const files: FileDetail[] = e.value;
  const tracks = files.map(({ track }) => track);
  await musicStore.updateMusicOrder(tracks);
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
