<template>
  <FilesTree :store="store" :uploadURL="uploadURL" />
</template>

<script setup lang="ts">
import { computed } from "vue";
import FilesTree from "@/features/files/components/FilesTree.vue";
import { makeUploadURL } from "@/features/files/api";
import { useVideoStore } from "@/features/files/stores";

const store = useVideoStore();
const uploadURL = computed(() => makeUploadURL(store.mediaType));
</script>
