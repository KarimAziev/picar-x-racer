<template>
  <DataTable
    size="small"
    :value="files"
    :loading="loading"
    @rowReorder="onRowReorder"
  >
    <template #header>
      <div class="flex justify-between items-center">
        <div class="flex gap-x-4">
          <SelectField
            field="settings.music.mode"
            label="Default Mode"
            class="w-full min-w-52"
            :options="musicModes"
            v-model="musicStore.player.mode"
            @update:model-value="handleUpdateMusicMode"
          />
        </div>
      </div>
    </template>
    <Column rowReorder headerStyle="width: 3rem" :reorderableColumn="false" />
    <Column
      class="max-w-[100px] whitespace-nowrap overflow-hidden text-ellipsis md:max-w-[120px] xl:max-w-[250px]"
      field="track"
      header="Track"
    >
      <template #body="slotProps">
        <span v-tooltip="slotProps.data.track">{{ slotProps.data.track }}</span>
      </template>
    </Column>
    <Column field="duration" header="Duration" class="w-20 !text-center">
      <template #body="slotProps">
        {{ secondsToReadableString(slotProps.data.duration) }}
      </template>
    </Column>

    <Column :exportable="false" header="Actions" class="w-[100px]">
      <template #body="slotProps">
        <ButtonGroup>
          <Button
            size="small"
            v-if="isPlaying(slotProps.data.track)"
            @click="pauseTrack"
            icon="pi pi-pause"
            v-tooltip="'Pause'"
            text
            aria-label="Pause"
          />
          <Button
            @click="playTrack(slotProps.data.track)"
            v-else
            size="small"
            v-tooltip="'Play'"
            icon="pi pi-play-circle"
            text
            aria-label="Play"
          />
          <Button
            rounded
            size="small"
            v-tooltip="'Download'"
            severity="secondary"
            text
            icon="pi pi-download"
            @click="handleDownloadFile(slotProps.data.track)"
          >
          </Button>
          <Button
            size="small"
            v-tooltip="'Remove'"
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
    class="mt-4"
    :auto="true"
    :disabled="loading"
    mode="basic"
    size="small"
    name="file"
    chooseLabel="Add"
    :url="apiURL"
    multiple
    accept="audio/*"
    :customUpload="true"
    @uploader="uploader"
  >
  </FileUpload>
</template>

<script setup lang="ts">
import { mediaType, FileDetail, MusicMode } from "@/features/music";
import { computed } from "vue";
import type { DataTableRowReorderEvent } from "primevue/datatable";
import FileUpload from "primevue/fileupload";
import ButtonGroup from "primevue/buttongroup";
import SelectField from "@/ui/SelectField.vue";
import { useFileUploader } from "@/composables/useFileUploader";

import { secondsToReadableString } from "@/util/time";
import { startCase } from "@/util/str";
import { useMusicStore } from "@/features/music";

const apiURL = `/api/files/upload/${mediaType}`;

const musicStore = useMusicStore();
const musicModes = Object.values(MusicMode).map((value) => ({
  value,
  label: startCase(value),
}));

const { uploader } = useFileUploader({
  url: apiURL,
  onBeforeStart: () => {
    musicStore.loading = true;
  },
  onFinish: async () => {
    await musicStore.fetchData();
    await handleUpdateOrder(musicStore.data);
    musicStore.loading = false;
  },
});

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
};

const handleDownloadFile = (track: string) => {
  musicStore.downloadFile(track);
};
</script>
