<template>
  <TreeTable
    :rowHover="true"
    v-model:selectionKeys="fields.model"
    :value="items"
    :loading="loading"
    dataKey="key"
    :metaKeySelection="false"
    selectionMode="single"
    filterMode="strict"
    :filters="filters"
    @update:selectionKeys="updateDebounced"
    scrollHeight="350px"
    :virtualScrollerOptions="{
      itemSize: 30,
      lazy: true,
      showLoader: true,
      orientation: 'vertical',
    }"
  >
    <Column field="name" header="Model" expander> </Column>
    <Column field="type" header="Type"></Column>
    <Column :exportable="false" header="Actions">
      <template #body="slotProps">
        <ButtonGroup class="whitespace-nowrap">
          <Button
            rounded
            v-tooltip="'Download file'"
            severity="secondary"
            text
            icon="pi pi-download"
            :disabled="slotProps.node?.data?.type !== 'File'"
            @click="handleDownloadFile(slotProps.node.key)"
          >
          </Button>
          <Button
            icon="pi pi-trash"
            size="small"
            severity="danger"
            :disabled="slotProps.node?.data?.type !== 'File'"
            text
            @click="handleRemove(slotProps.node.key)"
          />
        </ButtonGroup>
      </template>
    </Column>
  </TreeTable>
</template>

<script setup lang="ts">
import TreeTable, { TreeTableFilterMeta } from "primevue/treetable";
import ButtonGroup from "primevue/buttongroup";
import { useStore as useDetectionStore } from "@/features/detection/store";
import Button from "primevue/button";
import { inject, computed } from "vue";
import { downloadFile, removeFile } from "@/features/settings/api";
import type { DetectionFields } from "@/features/detection/composables/useDetectionFields";

const fields = inject<DetectionFields["fields"]>("fields");
const filters = inject<TreeTableFilterMeta>("filters");
const updateDebounced =
  inject<DetectionFields["updateDebounced"]>("updateDebounced");
const detectionStore = useDetectionStore();

if (!fields || !filters || !updateDebounced || !detectionStore) {
  throw new Error(
    "fields, filters, updateDebounced, and detectionStore must be provided!",
  );
}

const items = computed(() => detectionStore.detectors);
const loading = computed(() => detectionStore.loading);

const handleRemove = async (key: string) => {
  await removeFile("data", key);
  await detectionStore.fetchModels();
};

const handleDownloadFile = (key: string) => {
  downloadFile("data", key);
};
</script>
