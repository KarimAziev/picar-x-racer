<template>
  <FileUpload
    mode="basic"
    multiple
    name="file"
    accept=".pt,.tflite"
    :auto="true"
    chooseLabel="Add model"
    :customUpload="true"
    @uploader="uploader"
  />
</template>

<script setup lang="ts">
import { useFileUploader } from "@/composables/useFileUploader";
import { useDetectionStore } from "@/features/detection";

const store = useDetectionStore();
const mediaType = "data";

const { uploader } = useFileUploader({
  url: `/api/files/upload/${mediaType}`,
  onBeforeStart: () => {
    store.loading = true;
  },
  onFinish: () => {
    store.loading = false;
  },
});
</script>

<style scoped lang="scss">
:deep(.p-fileupload-basic) {
  margin: 2rem 0;
}
</style>
