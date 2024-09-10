<template>
  <Panel :toggleable="toggleable" :header="header">
    <slot></slot>
    <FileList
      :files="files"
      :fetch-data="fetchData"
      :remove-file="removeFile"
      :download-file="downloadFile"
    />
    <FileUpload
      :auto="true"
      :disabled="loading"
      mode="basic"
      size="small"
      name="file"
      @upload="onUpload($event)"
      chooseLabel="Add"
      :url="url"
      :multiple="false"
      accept="audio/*"
    >
    </FileUpload>
  </Panel>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { default as FileUpload } from "primevue/fileupload";
import Panel from "primevue/panel";

import type { FileUploadUploadEvent } from "primevue/fileupload";
import FileList from "@/features/settings/components/FileList.vue";

import { useMessagerStore } from "@/features/messager/store";

const messager = useMessagerStore();
const loading = ref(false);

const props = defineProps<{
  fetchData?: () => Promise<any>;
  header?: string;
  url: string;
  files: string[];
  downloadFile?: (file: string) => Promise<any>;
  removeFile?: (file: string) => Promise<any>;
  toggleable?: boolean;
}>();

const onUpload = async (_event: FileUploadUploadEvent) => {
  if (props.fetchData) {
    await props.fetchData();
  }
  messager.info("File Uploaded");
};
</script>

<style scoped lang="scss"></style>
