<template>
  <TreeTable
    :rowHover="true"
    v-model:selectionKeys="selectedValue"
    :value="items"
    dataKey="key"
    :metaKeySelection="false"
    selectionMode="single"
  >
    <template #header>
      <ButtonGroup class="button-group">
        <ObjectDetectionSwitch label="Toggle object detection" />
        <FileUpload
          mode="basic"
          name="model[]"
          url="/api/upload/data"
          @upload="camStore.fetchModels"
          :auto="true"
          chooseLabel="Add"
        />
      </ButtonGroup>
    </template>
    <Column field="name" header="Name" expander> </Column>
    <Column field="type" header="Type"></Column>
    <Column :exportable="false" header="Actions">
      <template #body="slotProps">
        <ButtonGroup class="button-group">
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
import ButtonGroup from "primevue/buttongroup";
import TreeTable from "primevue/treetable";
import { useMessagerStore } from "@/features/messager/store";
import { downloadFile, removeFile } from "@/features/settings/api";
import { useCameraStore, useSettingsStore } from "@/features/settings/stores";
import { onMounted, ref, watch, computed } from "vue";
import ObjectDetectionSwitch from "@/features/settings/components/ObjectDetectionSwitch.vue";

const store = useSettingsStore();
const camStore = useCameraStore();
const selectedValue = ref(
  store.settings.video_feed_detect_mode
    ? { [store.settings.video_feed_detect_mode]: true }
    : {},
);

const handleDownloadFile = (value: string) => {
  downloadFile("data", value);
};

watch(
  () => selectedValue.value,
  async (newVal) => {
    store.settings.video_feed_detect_mode = Object.keys(newVal)[0] || null;
    await camStore.updateCameraParams({
      video_feed_detect_mode: store.settings.video_feed_detect_mode,
    });
    await camStore.fetchModels();
  },
);

onMounted(async () => {
  await camStore.fetchModels();
});

const items = computed(() => camStore.detectors);

const handleRemove = async (key: string) => {
  const messager = useMessagerStore();
  try {
    await removeFile("data", key);
    await camStore.fetchModels();
  } catch (error) {
    messager.handleError(error);
  }
};
</script>

<style scoped lang="scss">
.tag {
  cursor: pointer;
}
.language {
  width: 60px;
}
textarea {
  width: 100%;
}

.button-group {
  white-space: nowrap;
}

@media (min-width: 576px) {
  .language {
    width: 100px;
  }
}

@media (min-width: 1200px) {
  textarea {
    width: 200px;
  }
}
</style>
