<template>
  <DataTable
    :value="files"
    :loading="loading"
    dataKey="track"
    scrollable
    v-model:selection="markedItems"
    scrollHeight="400px"
    :virtualScrollerOptions="{
      itemSize: itemSize,
      lazy: true,
      showLoader: true,
      orientation: 'vertical',
    }"
  >
    <template #header>
      <div class="flex flex-col gap-2">
        <div>Act on {{ markedItemsLen }} files</div>
        <ButtonGroup>
          <Button
            label="Download"
            @click="handleDownloadMarked"
            :disabled="batchButtonsDisabled"
            severity="secondary"
            icon="pi pi-download"
          >
          </Button>
          <Button
            label="Download archive"
            @click="handleDownloadArchive"
            :disabled="batchButtonsDisabled"
            severity="secondary"
            icon="pi pi-download"
          >
          </Button>
          <Button
            severity="danger"
            :disabled="batchButtonsDisabled"
            @click="handleRemoveMarked"
            label="Delete"
            icon="pi pi-trash"
          ></Button>
        </ButtonGroup>
      </div>
    </template>
    <template #empty>
      <div v-if="!loading" class="text-center">
        {{ emptyMessage }}
      </div>
    </template>

    <Column selectionMode="multiple" headerStyle="width: 3rem"></Column>
    <Column class="preview-col" header="Preview" field="preview">
      <template #body="slotProps">
        <div :style="`width: ${itemSize}px;`">
          <Photo
            v-if="slotProps.data.preview"
            className="thumbnail"
            :style="`width: ${itemSize}px;`"
            :src="`/api/files/video/preview?filename=${encodeURIComponent(slotProps.data.preview)}`"
            :width="itemSize"
            @click="openImage(slotProps.data)"
          />
          <i v-else class="pi pi-play" />
        </div>
      </template>
    </Column>

    <Column class="track-col" field="track" header="File"></Column>
    <Column field="duration" header="Duration" class="w-20 !text-center">
      <template #body="slotProps">
        {{ secondsToReadableString(slotProps.data.duration) }}
      </template>
    </Column>

    <Column :exportable="false" header="Actions">
      <template #body="slotProps">
        <ButtonGroup class="whitespace-nowrap">
          <Button
            rounded
            v-tooltip="'Download video'"
            severity="secondary"
            text
            :disabled="
              removing[slotProps.data.track] ||
              downloading[slotProps.data.track]
            "
            icon="pi pi-download"
            @click="handleDownloadFile(slotProps.data.track)"
          >
          </Button>
          <Button
            icon="pi pi-trash"
            outlined
            rounded
            :disabled="
              removing[slotProps.data.track] ||
              downloading[slotProps.data.track]
            "
            severity="danger"
            text
            @click="handleRemove(slotProps.data.track)"
          />
        </ButtonGroup>
      </template>
    </Column>
  </DataTable>

  <Dialog
    :header="selectedItem.track"
    content-class="sm:min-w-[600px] md:min-w-[700px] lg:min-w-[1000px] xl:min-[1200px] h-[85vh]"
    v-model:visible="popupStore.isPreviewImageOpen"
    dismissableMask
    modal
    @after-hide="removeKeyEventListeners"
  >
    <div class="flex flex-col w-full justify-between h-full">
      <div class="flex flex-nowrap justify-between w-full text-center my-auto">
        <div class="flex-1">
          <button
            @click="handlePrevImagePreview"
            class="w-full h-full text-left hover:text-robo-color-primary disabled:hover:bg-transparent disabled:opacity-60 px-4"
          >
            <i class="pi pi-chevron-left" />
          </button>
        </div>
        <video
          ref="videoRef"
          controls
          autoplay
          :poster="selectedPosterURL || undefined"
          class="h-auto max-w-[80%]"
        >
          <source :src="selectedItemURL" type="video/mp4" />
          Your browser does not support the video tag.
        </video>

        <div class="flex-1">
          <button
            @click="handleNextImagePreview"
            class="w-full h-full text-right hover:text-robo-color-primary disabled:hover:bg-transparent disabled:opacity-60 px-4"
          >
            <i class="pi pi-chevron-right" />
          </button>
        </div>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { watch, computed, onMounted, ref, useTemplateRef, nextTick } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import ButtonGroup from "primevue/buttongroup";
import { mediaType } from "@/features/settings/stores/video";
import { usePopupStore, useVideoStore } from "@/features/settings/stores";
import { cycleValue } from "@/util/cycleValue";
import { formatKeyEventItem } from "@/util/keyboard-util";
import { secondsToReadableString } from "@/util/time";
import Photo from "@/ui/Photo.vue";
import type { FileItem } from "@/features/settings/stores/video";

const store = useVideoStore();

const popupStore = usePopupStore();
const loading = computed(() => store.loading);
const downloading = ref<Record<string, boolean>>({});
const removing = ref<Record<string, boolean>>({});
const emptyMessage = computed(() => store.emptyMessage);

const videoRef = useTemplateRef("videoRef");

const selectedItem = ref<FileItem>({ preview: null, track: "", duration: 0 });
const selectedItemURL = computed(() =>
  selectedItem.value.track
    ? `/api/files/stream/${mediaType}?filename=${encodeURIComponent(selectedItem.value.track)}`
    : selectedItem.value.track,
);

const selectedPosterURL = computed(() =>
  selectedItem.value.preview
    ? `/api/files/video/preview?filename=${encodeURIComponent(selectedItem.value.preview)}`
    : selectedItem.value.preview,
);

const itemSize = 50;

const files = computed(() => store.data);
const markedItems = ref<FileItem[]>([]);

const markedItemsLen = computed(() => markedItems.value.length);
const batchButtonsDisabled = computed(
  () =>
    !markedItemsLen.value ||
    Object.keys({ ...removing.value, ...downloading.value }).length > 0,
);

const handleNextImagePreview = () => {
  videoRef.value?.pause();
  const nextImg = cycleValue(
    ({ track }) => track === selectedItem.value.track,
    files.value,
    1,
  );
  selectedItem.value = nextImg;
  nextTick(() => {
    if (videoRef.value) {
      videoRef.value.load();
      videoRef.value.play();
    }
  });
  if (!popupStore.isPreviewImageOpen) {
    popupStore.isPreviewImageOpen = true;
  }
};

const handlePrevImagePreview = () => {
  videoRef.value?.pause();
  const nextImg = cycleValue(
    ({ track }) => track === selectedItem.value.track,
    files.value,
    -1,
  );
  selectedItem.value = nextImg;
  nextTick(() => {
    if (videoRef.value) {
      videoRef.value.load();
      videoRef.value.play();
    }
  });
  if (!popupStore.isPreviewImageOpen) {
    popupStore.isPreviewImageOpen = true;
  }
};

const handleDownloadFile = (track: string) => {
  store.downloadFile(track);
};

const handleRemoveMarked = async () => {
  const names = markedItems.value.map((file) => file.track);
  markedItems.value.forEach((file) => {
    removing.value[file.track] = true;
  });
  await store.batchRemoveFiles(names);

  removing.value = {};
};

const handleDownloadMarked = async () => {
  for (let i = 0; i < markedItems.value.length; i++) {
    const { track } = markedItems.value[i];
    downloading.value[track] = true;
    await store.downloadFile(track);
  }
  downloading.value = {};
};

const handleDownloadArchive = async () => {
  const filenames = markedItems.value.map(({ track }) => track);
  const downloadingUrls = markedItems.value.reduce(
    (acc, { track }) => {
      acc[track] = true;
      return acc;
    },
    {} as Record<string, boolean>,
  );
  downloading.value = downloadingUrls;
  await store.downloadFilesArchive(filenames);
  downloading.value = {};
};

const handleRemove = async (track: string) => {
  await store.removeFile(track);
};

const keyHandlers: { [key: string]: Function } = {
  ArrowLeft: handlePrevImagePreview,
  ArrowRight: handleNextImagePreview,
};

const handleKeyUp = (event: KeyboardEvent) => {
  const key = formatKeyEventItem(event);
  if (keyHandlers[key]) {
    keyHandlers[key]();
  }
};

const addKeyEventListeners = () => {
  window.addEventListener("keyup", handleKeyUp);
};

const removeKeyEventListeners = () => {
  window.removeEventListener("keyup", handleKeyUp);
};

const openImage = (item: FileItem) => {
  selectedItem.value = item;
  addKeyEventListeners();
  popupStore.isPreviewImageOpen = true;
};

watch(
  () => store.data,
  (newData) => {
    const hash = new Set(newData.map((item) => item.track));
    markedItems.value = markedItems.value.filter((it) => hash.has(it.track));
  },
);

onMounted(store.fetchData);
</script>
