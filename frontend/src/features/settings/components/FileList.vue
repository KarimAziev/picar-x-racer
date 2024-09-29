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
  >
    <img :src="selectedImage" class="full-image" />
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import { useMessagerStore } from "@/features/messager/store";
import { usePopupStore } from "@/features/settings/stores";

const messager = useMessagerStore();
const popupStore = usePopupStore();
const loading = ref(false);

const selectedImage = ref("");
const props = defineProps<{
  files: string[];
  fetchData?: () => Promise<any>;
  downloadFile?: (file: string) => void;
  removeFile?: (file: string) => Promise<any>;
}>();

const files = computed(() => props.files.map((filename) => ({ filename })));

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

const openImage = (filename: string) => {
  selectedImage.value = getPreviewUrl(filename);
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
.files {
  display: flex;
  list-style: none;
  flex-direction: column;
  justify-content: space-between;
}
.filerow {
  display: flex;
  gap: 5px;
  justify-content: space-between;
}
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
</style>
