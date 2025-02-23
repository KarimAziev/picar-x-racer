<template>
  <DataTable
    :value="images"
    :loading="loading"
    dataKey="src"
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
    <Column class="preview-col" header="Preview" field="src">
      <template #body="slotProps">
        <Photo
          className="thumbnail"
          :src="slotProps.data.src"
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
    :content-class="
      isMaximized
        ? 'w-full h-full'
        : 'sm:w-[600px] md:w-[700px] lg:w-[1000px] xl:w-[1200px] h-[85vh]'
    "
    class="gallery-popup"
    :header="header"
    maximizable
    v-model:visible="popupStore.isPreviewImageOpen"
    dismissableMask
    modal
    @maximize="handleMaximize"
    @unmaximize="handleUnmaximize"
  >
    <Gallery
      v-model:activeIndex="activeIndex"
      :images="images"
      :numVisible="10"
      :maxWidth="maxWidth"
      :minWidth="minWidth"
      :maxHeight="maxHeight"
      :minHeight="minHeight"
    >
    </Gallery>
  </Dialog>
</template>

<script setup lang="ts">
import { FileItem } from "@/features/settings/stores/images";
import { watch, computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import ButtonGroup from "primevue/buttongroup";
import { usePopupStore, useImageStore } from "@/features/settings/stores";
import Photo from "@/ui/Photo.vue";
import { isNumber } from "@/util/guards";
import { useWindowSize } from "@/composables/useWindowSize";
import Gallery from "@/ui/Gallery.vue";
import { takePercentage } from "@/util/number";

const store = useImageStore();

const popupStore = usePopupStore();
const loading = computed(() => store.loading);
const downloading = ref<Record<string, boolean>>({});
const removing = ref<Record<string, boolean>>({});
const emptyMessage = computed(() => store.emptyMessage);

const itemSize = 50;

const isMaximized = ref(false);

const wndSize = useWindowSize();
const minWidth = computed(() => Math.min(640, wndSize.width.value));

const maxWidth = computed(() =>
  Math.max(minWidth.value, takePercentage(wndSize.width.value, 90)),
);
const minHeight = computed(() => takePercentage(wndSize.height.value, 75));

const maxHeight = computed(() => minHeight.value);

const handleMaximize = () => {
  isMaximized.value = true;
};

const handleUnmaximize = () => {
  isMaximized.value = false;
};

const activeIndex = ref<number>(0);

const images = computed(() =>
  store.data.map(({ url, name }) => ({
    name,
    title: name,
    url: url,
    alt: name,
    src: `/api/files/image/preview?filename=${encodeURIComponent(url)}`,
  })),
);

const header = computed(() => {
  const result = isNumber(activeIndex.value)
    ? store.data[activeIndex.value]?.name
    : undefined;
  return result;
});
const markedItems = ref<FileItem[]>([]);

const markedItemsLen = computed(() => markedItems.value.length);
const batchButtonsDisabled = computed(
  () =>
    !markedItemsLen.value ||
    Object.keys({ ...removing.value, ...downloading.value }).length > 0,
);

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

const openImage = (item: FileItem) => {
  activeIndex.value = images.value.findIndex(
    ({ title, url }) => item.name === title && url === item.url,
  );
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
<style scoped lang="scss">
.gallery-popup.p-dialog {
  background-color: transparent;
}
</style>
