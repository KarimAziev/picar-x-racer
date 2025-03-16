<template>
  <Cell>
    <div class="justify-self-end">
      <ButtonGroup class="whitespace-nowrap" v-if="isUploadingRow">
        <Button
          icon="pi pi-times"
          outlined
          rounded
          severity="danger"
          text
          v-tooltip="'Cancel upload'"
          @click="handleCancelUpload"
        />
      </ButtonGroup>
      <ButtonGroup class="whitespace-nowrap" v-else>
        <Button
          rounded
          v-tooltip="'Download'"
          severity="secondary"
          text
          :disabled="disabled"
          icon="pi pi-download"
          @click="handleDownloadFile"
        ></Button>
        <Button
          icon="pi pi-trash"
          outlined
          rounded
          :disabled="disabled"
          severity="danger"
          text
          @click="handleRemoveFile"
        />
      </ButtonGroup>
    </div>
  </Cell>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { isNumber } from "@/util/guards";
import type { UploadingFileDetail } from "@/features/files/interface";

import Cell from "@/features/files/components/Cell.vue";

export interface Props extends Pick<UploadingFileDetail, "path" | "progress"> {
  disabled?: boolean;
}
const props = defineProps<Props>();

const isUploadingRow = computed(() => isNumber(props.progress));

const emit = defineEmits(["download", "remove", "rename", "upload:cancel"]);

const handleDownloadFile = () => {
  emit("download", props.path);
};

const handleRemoveFile = () => {
  emit("remove", props.path);
};

const handleCancelUpload = () => {
  emit("upload:cancel", props.path);
};
</script>
