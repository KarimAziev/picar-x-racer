<template>
  <FilesPanel
    :fetch-data="store.fetchData"
    toggleable
    header="Sounds"
    :url="apiURL"
    :files="store.data"
    :download-file="store.downloadFile"
    :remove-file="store.removeFile"
  >
    <FileList
      :files="store.defaultData"
      :fetch-data="store.fetchDefaultData"
      :download-file="store.downloadFile"
    />
  </FilesPanel>
</template>

<script setup lang="ts">
import FilesPanel from "@/features/settings/components/FilesPanel.vue";
import FileList from "@/features/settings/components/FileList.vue";
import { useStore, mediaType } from "@/features/settings/stores/sounds";

const apiURL = `/api/upload/${mediaType}`;

const store = useStore();
</script>
