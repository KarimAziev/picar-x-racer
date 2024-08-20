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
  </FilesPanel>
</template>

<script setup lang="ts">
import FilesPanel from "@/features/settings/components/FilesPanel.vue";
import { useStore, mediaType } from "@/features/settings/stores/music";

const apiURL = `/api/upload/${mediaType}`;

const store = useStore();
</script>
