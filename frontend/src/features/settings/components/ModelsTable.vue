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
      <div class="header">
        <ObjectDetectionSettings />
      </div>
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
import { onMounted, ref, watch, computed } from "vue";
import ButtonGroup from "primevue/buttongroup";
import TreeTable from "primevue/treetable";
import ObjectDetectionSettings from "@/features/settings/components/ObjectDetectionSettings.vue";
import { useMessagerStore } from "@/features/messager/store";
import { downloadFile, removeFile } from "@/features/settings/api";
import { useCameraStore, useSettingsStore } from "@/features/settings/stores";
import { useAsyncDebounce } from "@/composables/useDebounce";
import { roundNumber } from "@/util/number";
import { isNumber } from "@/util/guards";

const NONE_KEY = "NONE";
const store = useSettingsStore();
const camStore = useCameraStore();
const selectedValue = ref(
  store.settings.video_feed_detect_mode
    ? { [store.settings.video_feed_detect_mode]: true }
    : {},
);

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

const handleDownloadFile = (value: string) => {
  downloadFile("data", value);
};

const updateCameraParams = useAsyncDebounce(async () => {
  await camStore.updateCameraParams({
    video_feed_model_img_size: store.settings.video_feed_model_img_size,
    video_feed_detect_mode: store.settings.video_feed_detect_mode,
    video_feed_confidence: isNumber(store.settings.video_feed_confidence)
      ? roundNumber(store.settings.video_feed_confidence, 1)
      : store.settings.video_feed_confidence,
  });
}, 2000);

watch(
  () => selectedValue.value,
  async (newVal) => {
    const nextValue = Object.keys(newVal)[0] || null;
    store.settings.video_feed_detect_mode =
      nextValue === NONE_KEY ? null : nextValue;
    updateCameraParams();
  },
);

watch(
  () => selectedValue.value,
  async (newVal) => {
    store.settings.video_feed_detect_mode = Object.keys(newVal)[0] || null;

    await updateCameraParams();
    await camStore.fetchModels();
  },
);

watch(() => store.settings.video_feed_model_img_size, updateCameraParams);
watch(() => store.settings.video_feed_detect_mode, updateCameraParams);
watch(() => store.settings.video_feed_confidence, updateCameraParams);

onMounted(camStore.fetchModels);
</script>

<style scoped lang="scss">
.header {
  display: flex;
}
.button-group {
  white-space: nowrap;
}
:deep(.p-inputtext) {
  width: 90px;
}
</style>
