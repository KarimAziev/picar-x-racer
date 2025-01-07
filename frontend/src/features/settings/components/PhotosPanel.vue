<template>
  <DataTable
    :value="files"
    :loading="loading"
    dataKey="url"
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
    <Column class="preview-col" header="Preview" field="url">
      <template #body="slotProps">
        <Photo
          className="thumbnail"
          :src="slotProps.data.url"
          :width="itemSize"
          @click="openImage(slotProps.data)"
        />
      </template>
    </Column>

    <Column class="track-col" field="name" header="File"></Column>

    <Column :exportable="false" header="Actions">
      <template #body="slotProps">
        <ButtonGroup class="whitespace-nowrap">
          <Button
            rounded
            v-tooltip="'Download photo'"
            severity="secondary"
            text
            :disabled="
              removing[slotProps.data.url] || downloading[slotProps.data.url]
            "
            icon="pi pi-download"
            @click="handleDownloadFile(slotProps.data.name)"
          >
          </Button>
          <Button
            icon="pi pi-trash"
            outlined
            rounded
            :disabled="
              removing[slotProps.data.url] || downloading[slotProps.data.url]
            "
            severity="danger"
            text
            @click="handleRemove(slotProps.data.name)"
          />
        </ButtonGroup>
      </template>
    </Column>
  </DataTable>

  <Dialog
    v-model:visible="popupStore.isPreviewImageOpen"
    class="image-dialog"
    dismissableMask
    modal
    @after-hide="removeKeyEventListeners"
  >
    <Photo className="w-full h-auto" :src="selectedImage?.url" :width="380" />
    <ButtonGroup class="flex justify-center">
      <Button
        text
        aria-label="Previous image"
        icon="pi pi-chevron-left"
        @click="handlePrevImagePreview"
      ></Button>
      <div class="text-center flex-auto">{{ selectedImage.name }}</div>
      <Button
        text
        aria-label="Next image"
        icon="pi pi-chevron-right"
        @click="handleNextImagePreview"
      ></Button>
    </ButtonGroup>
  </Dialog>
</template>

<script setup lang="ts">
import { FileItem } from "@/features/settings/stores/images";
import { watch, computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import ButtonGroup from "primevue/buttongroup";

import { usePopupStore, useImageStore } from "@/features/settings/stores";
import { cycleValue } from "@/util/cycleValue";
import { formatKeyEventItem } from "@/util/keyboard-util";
import Photo from "@/ui/Photo.vue";

const store = useImageStore();

const popupStore = usePopupStore();
const loading = computed(() => store.loading);
const downloading = ref<Record<string, boolean>>({});
const removing = ref<Record<string, boolean>>({});
const emptyMessage = computed(() => store.emptyMessage);

const selectedImage = ref({ url: "", name: "" });

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
  const nextImg = cycleValue(
    ({ url }) => url === selectedImage.value.url,
    files.value,
    1,
  );
  selectedImage.value.url = nextImg.url;
  selectedImage.value.name = nextImg.name;
  if (!popupStore.isPreviewImageOpen) {
    popupStore.isPreviewImageOpen = true;
  }
};

const handlePrevImagePreview = () => {
  const nextImg = cycleValue(
    ({ url }) => url === selectedImage.value.url,
    files.value,
    -1,
  );
  selectedImage.value.url = nextImg.url;
  selectedImage.value.name = nextImg.name;
  if (!popupStore.isPreviewImageOpen) {
    popupStore.isPreviewImageOpen = true;
  }
};

const handleDownloadFile = (name: string) => {
  store.downloadFile(name);
};

const handleRemoveMarked = async () => {
  const names = markedItems.value.map((file) => file.name);
  markedItems.value.forEach((file) => {
    removing.value[file.url] = true;
  });
  await store.batchRemoveFiles(names);

  removing.value = {};
};

const handleDownloadMarked = async () => {
  for (let i = 0; i < markedItems.value.length; i++) {
    const { name, url } = markedItems.value[i];
    downloading.value[url] = true;
    await store.downloadFile(name);
  }
  downloading.value = {};
};

const handleDownloadArchive = async () => {
  const filenames = markedItems.value.map(({ name }) => name);
  const downloadingUrls = markedItems.value.reduce(
    (acc, { url }) => {
      acc[url] = true;
      return acc;
    },
    {} as Record<string, boolean>,
  );
  downloading.value = downloadingUrls;
  await store.downloadFilesArchive(filenames);
  downloading.value = {};
};

const handleRemove = async (name: string) => {
  await store.removeFile(name);
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
  selectedImage.value.url = item.url;
  selectedImage.value.name = item.name;
  addKeyEventListeners();
  popupStore.isPreviewImageOpen = true;
};

watch(
  () => store.data,
  (newData) => {
    const hash = new Set(newData.map((item) => item.url));
    markedItems.value = markedItems.value.filter((it) => hash.has(it.url));
  },
);

onMounted(store.fetchData);
</script>
