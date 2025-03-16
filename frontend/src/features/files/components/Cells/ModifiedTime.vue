<template>
  <Cell>
    <span v-if="modified !== null">
      {{ formatModifiedTime(modified) }}
    </span>
  </Cell>
</template>

<script setup lang="ts">
import type { UploadingFileDetail } from "@/features/files/interface";

import Cell from "@/features/files/components/Cell.vue";
import { formatModifiedTime } from "@/features/files/components/util";

export interface Props extends Pick<UploadingFileDetail, "modified"> {}
defineProps<Props>();
</script>
