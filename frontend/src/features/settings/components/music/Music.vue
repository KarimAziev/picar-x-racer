<template>
  <DataTable
    size="small"
    :value="files"
    :loading="loading"
    @rowReorder="onRowReorder"
  >
    <Column rowReorder headerStyle="width: 3rem" :reorderableColumn="false" />
    <Column
      class="max-w-[100px] whitespace-nowrap overflow-hidden text-ellipsis md:max-w-[120px] xl:max-w-[250px]"
      field="path"
      header="Track"
    >
      <template #body="slotProps">
        <span v-tooltip="slotProps.data.path">{{ slotProps.data.path }}</span>
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
            v-if="isPlaying(slotProps.data.path)"
            @click="pauseTrack"
            icon="pi pi-pause"
            v-tooltip="'Pause'"
            text
            aria-label="Pause"
          />
          <Button
            @click="playTrack(slotProps.data.path)"
            v-else
            size="small"
            v-tooltip="'Play'"
            icon="pi pi-play-circle"
            text
            aria-label="Play"
          />
        </ButtonGroup>
      </template>
    </Column>
  </DataTable>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { DataTableRowReorderEvent } from "primevue/datatable";
import ButtonGroup from "primevue/buttongroup";

import { secondsToReadableString } from "@/util/time";
import { useMusicStore } from "@/features/music";
import { FileDetail } from "@/features/files/interface";

const musicStore = useMusicStore();

const files = computed(() => musicStore.data);
const loading = computed(() => musicStore.loading);

const isPlaying = (path: string) =>
  musicStore.player.track === path && musicStore.player.is_playing;

const playTrack = async (path: string) => {
  await musicStore.playTrack(path);
};

const pauseTrack = async () => {
  await musicStore.togglePlaying();
};
const handleUpdateOrder = async (files: FileDetail[]) => {
  const tracks = files.map(({ path }) => path);
  await musicStore.updateMusicOrder(tracks);
};

const onRowReorder = async (e: DataTableRowReorderEvent) => {
  const files: FileDetail[] = e.value;
  await handleUpdateOrder(files);
};
</script>
