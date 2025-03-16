<template>
  <button
    v-if="children"
    @click.stop="toggleExpand(path)"
    :class="`pi rounded-md bg-transparent transition-opacity duration-300 ease-in-out hover:opacity-70 hover:bg-button-text-primary-hover-background focus:opacity-70 focus:outline-none pi-chevron-${expandedNodes.has(path) ? 'down' : 'right'}`"
  />

  <div v-else class="ml-4" />
</template>

<script setup lang="ts">
import { inject, Ref } from "vue";

import { UploadingFileDetail } from "@/features/files/interface";

export interface Props extends Pick<UploadingFileDetail, "path" | "children"> {}

defineProps<Props>();

const emit = defineEmits(["toggle:expand"]);

const expandedNodes = inject<Ref<Set<string>>>("expandedNodes");
if (!expandedNodes) {
  throw new Error("Expanded nodes and marked nodes must be provided!");
}

const toggleExpand = (path: string) => {
  if (expandedNodes.value.has(path)) {
    expandedNodes.value.delete(path);
  } else {
    expandedNodes.value.add(path);
  }
  emit("toggle:expand", path);
};
</script>
