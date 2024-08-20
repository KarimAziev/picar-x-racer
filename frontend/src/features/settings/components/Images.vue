<template>
  <FileList
    :fetch-data="store.fetchData"
    :files="store.data"
    :download-file="store.downloadFile"
    :remove-file="store.removeFile"
  />
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useStore } from "@/features/settings/stores/images";
import FileList from "@/features/settings/components/FileList.vue";

const store = useStore();

onMounted(() => {
  store.fetchData();
});
</script>
