<template>
  <Cell>
    <span v-if="isDirectoryType(type)">{{ children_count }}&nbsp; items</span>
    <span v-else>{{ bytesToSize(size || 0, 0) }}</span>
  </Cell>
</template>

<script setup lang="ts">
import type { UploadingFileDetail } from "@/features/files/interface";
import { isDirectoryType } from "@/features/files/components/util";
import Cell from "@/features/files/components/Cell.vue";
import { bytesToSize } from "@/features/files/util";

export interface Props
  extends Pick<UploadingFileDetail, "size" | "type" | "children_count"> {
  disabled?: boolean;
}
defineProps<Props>();
</script>
