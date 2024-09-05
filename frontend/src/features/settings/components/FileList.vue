<template>
  <div class="files-wrapper">
    <Loading :loading="loading">
      <ul class="files">
        <li v-for="track in files" :key="track" class="filerow">
          <span class="filename">{{ track }}</span>
          <Button
            v-if="downloadFile"
            v-tooltip="'Download file'"
            severity="secondary"
            outlined
            icon="pi pi-download"
            @click="downloadFile(track)"
          >
          </Button>
          <Button
            severity="danger"
            v-tooltip="'Remove file'"
            text
            v-if="removeFile"
            icon="pi pi-times"
            @click="handleRemove(track)"
          ></Button>
        </li>
      </ul>
    </Loading>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import Button from "primevue/button";
import Loading from "@/ui/Loading.vue";
import { useMessagerStore } from "@/features/messager/store";

const messager = useMessagerStore();
const loading = ref(false);
const props = defineProps<{
  files: string[];
  fetchData?: () => Promise<any>;
  downloadFile?: (file: string) => void;
  removeFile?: (file: string) => Promise<any>;
}>();

const handleRemove = async (track: string) => {
  if (props.removeFile) {
    try {
      await props.removeFile(track);
      if (props.fetchData) {
        await props.fetchData();
      }
      messager.info("File Removed");
    } catch (err) {
      messager.error("Error: File is not removed ");
    }
  }
};

onMounted(async () => {
  loading.value = true;
  if (props.fetchData) {
    try {
      await props.fetchData();
    } catch (_) {
    } finally {
      loading.value = false;
    }
  }
});
</script>

<style scoped lang="scss">
.files {
  display: flex;
  list-style: none;
  flex-direction: column;
  justify-content: space-between;
}
.filerow {
  display: flex;
  gap: 5px;
  justify-content: space-between;
}
.filename {
  min-width: 500px;
}
</style>
