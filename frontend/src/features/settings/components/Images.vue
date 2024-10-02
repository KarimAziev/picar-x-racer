<template>
  <DataTable
    :value="files"
    :loading="loading"
    scrollable
    scrollHeight="400px"
    :virtualScrollerOptions="{
      itemSize: itemSize,
      lazy: true,
      showLoader: true,
      orientation: 'vertical',
    }"
  >
    <Column class="preview-col" header="Preview">
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
        <ButtonGroup class="button-group">
          <Button
            rounded
            v-tooltip="'Download photo'"
            severity="secondary"
            text
            icon="pi pi-download"
            @click="handleDownloadFile(slotProps.data.name)"
          >
          </Button>
          <Button
            icon="pi pi-trash"
            outlined
            rounded
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
    <Photo className="full-image" :src="selectedImage?.url" :width="380" />
    <ButtonGroup class="prev-next-buttons">
      <Button
        text
        aria-label="Previous image"
        icon="pi pi-chevron-left"
        @click="handlePrevImagePreview"
      ></Button>
      <div class="dialog-filename">{{ selectedImage.name }}</div>
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
import { useStore, FileItem } from "@/features/settings/stores/images";
import { computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import ButtonGroup from "primevue/buttongroup";

import { usePopupStore } from "@/features/settings/stores";
import { cycleValue } from "@/util/cycleValue";
import { formatKeyEventItem } from "@/util/keyboard-util";
import Photo from "@/ui/Photo.vue";

const store = useStore();

const popupStore = usePopupStore();
const loading = ref(false);

const selectedImage = ref({ url: "", name: "" });

const itemSize = 50;

const files = computed(() => store.data);

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

const handleRemove = async (name: string) => {
  await store.removeFile(name);
  await store.fetchData();
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

onMounted(async () => {
  loading.value = true;
  await store.fetchData();
  loading.value = false;
});
</script>
<style scoped lang="scss">
.button-group {
  white-space: nowrap;
}
:deep(.thumbnail) {
  cursor: pointer;
}

.image-dialog .full-image {
  width: 100%;
  height: auto;
}

.prev-next-buttons {
  display: flex;
  justify-content: center;
}
.dialog-filename {
  flex: auto;
  text-align: center;
}
</style>
