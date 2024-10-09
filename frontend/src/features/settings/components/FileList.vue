<template>
  <DataTable :value="files" :loading="loading">
    <Column class="preview-col" header="Preview">
      <template #body="slotProps">
        <img
          :src="getPreviewUrl(slotProps.data.filename)"
          class="thumbnail"
          @click="openImage(slotProps.data.filename)"
        />
      </template>
    </Column>

    <Column class="track-col" field="filename" header="File"></Column>

    <Column :exportable="false" header="Actions">
      <template #body="slotProps">
        <ButtonGroup class="button-group">
          <Button
            rounded
            v-tooltip="'Download file'"
            severity="secondary"
            text
            icon="pi pi-download"
            @click="handleDownloadFile(slotProps.data.filename)"
          >
          </Button>
          <Button
            icon="pi pi-trash"
            outlined
            rounded
            severity="danger"
            text
            @click="handleRemove(slotProps.data.filename)"
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
    <img :src="selectedImage?.url" class="full-image" />
    <ButtonGroup class="prev-next-buttons">
      <Button
        text
        aria-label="Previous image"
        icon="pi pi-chevron-left"
        @click="handlePrevImagePreview"
      ></Button>
      <div class="dialog-filename">{{ selectedImage.filename }}</div>
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
import { computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import ButtonGroup from "primevue/buttongroup";
import { useMessagerStore } from "@/features/messager/store";
import { usePopupStore } from "@/features/settings/stores";
import { cycleValue } from "@/util/cycleValue";

import { useKeyboardHandlers } from "@/composables/useKeyboardHandlers";

const messager = useMessagerStore();
const popupStore = usePopupStore();
const loading = ref(false);

const selectedImage = ref({ url: "", filename: "" });

const props = defineProps<{
  files: string[];
  fetchData?: () => Promise<any>;
  downloadFile?: (file: string) => void;
  removeFile?: (file: string) => Promise<any>;
}>();

const files = computed(() => props.files.map((filename) => ({ filename })));

const handleNextImagePreview = () => {
  const nextImg = cycleValue(selectedImage.value.filename, props.files, 1);
  selectedImage.value.url = getPreviewUrl(nextImg);
  selectedImage.value.filename = nextImg;
  if (!popupStore.isPreviewImageOpen) {
    popupStore.isPreviewImageOpen = true;
  }
};

const handlePrevImagePreview = () => {
  const nextImg = cycleValue(selectedImage.value.filename, props.files, -1);
  selectedImage.value.url = getPreviewUrl(nextImg);
  selectedImage.value.filename = nextImg;
  if (!popupStore.isPreviewImageOpen) {
    popupStore.isPreviewImageOpen = true;
  }
};

const getPreviewUrl = (filename: string) => {
  return `/api/preview/${filename}`;
};

const handleDownloadFile = (filename: string) => {
  if (props.downloadFile) {
    props.downloadFile(filename);
  }
};

const handleRemove = async (filename: string) => {
  if (props.removeFile) {
    try {
      await props.removeFile(filename);
      if (props.fetchData) {
        await props.fetchData();
      }
    } catch (err) {
      messager.error("Error: File is not removed ");
    }
  }
};

const keyHandlers: { [key: string]: Function } = {
  ArrowLeft: handlePrevImagePreview,
  ArrowRight: handleNextImagePreview,
};

const { addKeyEventListeners, removeKeyEventListeners } =
  useKeyboardHandlers(keyHandlers);

const openImage = (filename: string) => {
  selectedImage.value.url = getPreviewUrl(filename);
  selectedImage.value.filename = filename;
  addKeyEventListeners();
  popupStore.isPreviewImageOpen = true;
};

onMounted(async () => {
  loading.value = true;
  if (props.fetchData) {
    try {
      await props.fetchData();
    } catch (_) {
    } finally {
      loading.value = false;
    }
  }
});
</script>

<style scoped lang="scss">
.button-group {
  white-space: nowrap;
}
.thumbnail {
  cursor: pointer;
  width: 50px;
  height: 50px;
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
