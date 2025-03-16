<template>
  <Cell>
    <span v-if="isDirectoryType(type) && children">
      {{ children.length }}&nbsp; items
    </span>
    <span v-else>{{ bytesToSize(size, 0) }}</span>
  </Cell>
</template>

<script setup lang="ts">
import type { UploadingFileDetail } from "@/features/files/interface";
import { isDirectoryType } from "@/features/files/components/util";
import Cell from "@/features/files/components/Cell.vue";
import { bytesToSize } from "@/features/files/util";

export interface Props
  extends Pick<UploadingFileDetail, "children" | "size" | "type"> {
  disabled?: boolean;
}
defineProps<Props>();
</script>
