<template>
  <div class="files-wrapper">
    <Loading :loading="loading">
      <DataTable :value="files" :loading="loading">
        <Column class="track-col" field="filename" header="File"></Column>

        <Column :exportable="false" header="Actions">
          <template #body="slotProps">
            <ButtonGroup class="button-group">
              <Button
                rounded
                v-tooltip="'Download file'"
                severity="secondary"
                text
                icon="pi pi-download"
                @click="slotProps.data.filename;"
              >
              </Button>
              <Button
                icon="pi pi-trash"
                outlined
                rounded
                severity="danger"
                text
                @click="handleRemove(slotProps.data.filename)"
              />
            </ButtonGroup>
          </template>
        </Column>
      </DataTable>
    </Loading>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
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

const files = computed(() => props.files.map((filename) => ({ filename })));

const handleRemove = async (filename: string) => {
  if (props.removeFile) {
    try {
      await props.removeFile(filename);
      if (props.fetchData) {
        await props.fetchData();
      }
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
.button-group {
  white-space: nowrap;
}
</style>
