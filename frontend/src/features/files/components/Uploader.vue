<template>
  <FileUpload
    :auto="true"
    :disabled="loading"
    mode="basic"
    size="small"
    name="file"
    multiple
    outlined
    :customUpload="true"
    @uploader="uploader"
    v-bind="props"
  ></FileUpload>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { FileStore } from "@/features/files/store-fabric";
import type { UploadingFileDetail } from "@/features/files/interface";
import type { FileUploadProps } from "primevue/fileupload";
import { uploadingFileToRow } from "@/features/files/components/util";
import { useFileUploader } from "@/composables/useFileUploader";

export interface Props
  extends Omit<
    FileUploadProps,
    | "customUpload"
    | "multiple"
    | "disabled"
    | "auto"
    | "basic"
    | "name"
    | "mode"
  > {
  url: string;
  store: FileStore;
}

const props = withDefaults(defineProps<Props>(), {
  chooseLabel: "Upload",
});

const loading = computed(() => props.store.loading);
const currentDir = computed(() => props.store.dir);

const { uploader, cancelSources } = useFileUploader({
  url: props.url || "",
  dir: currentDir,
  onBeforeStart: (files, dir) => {
    const rows: [string, UploadingFileDetail][] = files.map((file) => {
      const row = uploadingFileToRow(file, 0, dir);
      return [row.path, row];
    });

    const uploadingData = Object.fromEntries(rows);

    props.store.uploadingData = {
      ...props.store.uploadingData,
      ...uploadingData,
    };
  },
  onProgress: (file, progress, dir) => {
    const row = uploadingFileToRow(file, progress, dir);

    props.store.uploadingData[row.path] = row;
  },
  onFinishFile: (file, dir) => {
    const row = uploadingFileToRow(file, 100, dir);
    if (props.store.uploadingData[row.path]) {
      delete props.store.uploadingData[row.path];
    }
  },
});

const handleCancelUpload = (filepath: string) => {
  if (cancelSources.value[filepath]) {
    cancelSources.value[filepath].cancel();
    if (props.store.uploadingData[filepath]) {
      delete props.store.uploadingData[filepath];
    }
  }
};

defineExpose({ handleCancelUpload, uploader, cancelSources });
</script>
