<template>
  <FilesTree :store="store" :uploadURL="uploadURL" />
</template>

<script setup lang="ts">
import { computed } from "vue";
import FilesTree from "@/features/files/components/FilesTree.vue";
import { useImageStore } from "@/features/files/stores";
import { makeUploadURL } from "@/features/files/api";

const store = useImageStore();

const uploadURL = computed(() => makeUploadURL(store.mediaType));
</script>
