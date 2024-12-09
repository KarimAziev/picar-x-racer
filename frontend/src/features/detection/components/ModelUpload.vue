<template>
  <FileUpload
    mode="basic"
    name="file"
    accept=".pt,.tflite"
    :auto="true"
    chooseLabel="Add model"
    @upload="handleUpload"
    :customUpload="true"
    @error="handleError"
    @uploader="uploader"
  />
</template>

<script setup lang="ts">
import { useModelUpload } from "@/features/detection/composables/useModelUpload";

const { uploader, handleUpload, handleError } = useModelUpload();
</script>

<style scoped lang="scss">
:deep(.p-fileupload-basic) {
  margin: 2rem 0;
}
</style>
