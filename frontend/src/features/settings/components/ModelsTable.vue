<template>
  <TreeTable
    :rowHover="true"
    v-model:selectionKeys="selectedValue"
    :value="items"
    :loading="loading"
    dataKey="key"
    :metaKeySelection="false"
    selectionMode="single"
    filterMode="lenient"
    :filters="filters"
    scrollHeight="400px"
    :virtualScrollerOptions="{
      itemSize: 30,
      lazy: true,
      showLoader: true,
      orientation: 'vertical',
    }"
  >
    <template #header>
      <div class="header align-center">
        <div class="title">
          Current model: &nbsp;{{
            camStore.data.video_feed_detect_mode || "None"
          }}
        </div>
        <div class="search-wrapper">
          <div class="search-field">
            <IconField>
              <InputIcon class="pi pi-search" />
              <InputText
                id="search-models"
                v-model="filters['name'] as string"
                :pt="{ pcInput: { id: 'search-models' } }"
                placeholder="Search"
              />
            </IconField>
          </div>
        </div>
      </div>

      <div class="flex">
        <Field label="Detection" class="align-center">
          <ToggleSwitch
            inputId="video_feed_object_detection"
            v-tooltip="'Toggle object detection'"
            v-model="camStore.data.video_feed_object_detection"
          />
        </Field>

        <NumberField
          @keydown.stop="doNothing"
          @keyup.stop="doNothing"
          @keypress.stop="doNothing"
          showButtons
          label="Img size"
          inputId="video_feed_model_img_size"
          :loading="camStore.loadingData.video_feed_model_img_size"
          v-model="camStore.data.video_feed_model_img_size"
          :step="10"
        />
        <NumberField
          @keydown.stop="doNothing"
          @keyup.stop="doNothing"
          @keypress.stop="doNothing"
          field="video_feed_confidence"
          label="Confidence"
          v-model="camStore.data.video_feed_confidence"
          :loading="camStore.loadingData.video_feed_confidence"
          :min="0.1"
          :max="1.0"
          :step="0.1"
        />
      </div>
    </template>
    <Column field="name" header="Model" expander> </Column>
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
  <FileUpload
    class="upload-field"
    mode="basic"
    name="model[]"
    url="/api/upload/data"
    @upload="camStore.fetchModels"
    :auto="true"
    chooseLabel="Add model"
  />
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from "vue";
import ButtonGroup from "primevue/buttongroup";
import TreeTable, { TreeTableFilterMeta } from "primevue/treetable";
import InputIcon from "primevue/inputicon";
import IconField from "primevue/iconfield";
import ToggleSwitch from "primevue/toggleswitch";
import NumberField from "@/ui/NumberField.vue";
import { useMessagerStore } from "@/features/messager/store";
import { downloadFile, removeFile } from "@/features/settings/api";
import { useCameraStore, useSettingsStore } from "@/features/settings/stores";
import { useAsyncDebounce } from "@/composables/useDebounce";
import { roundNumber } from "@/util/number";
import { isNumber } from "@/util/guards";
import Field from "@/ui/Field.vue";

const store = useSettingsStore();
const camStore = useCameraStore();
const loading = computed(() => camStore.loading);
const selectedValue = ref(
  store.settings.video_feed_detect_mode
    ? { [store.settings.video_feed_detect_mode]: true }
    : {},
);

const items = computed(() => camStore.detectors);
const filters = ref<TreeTableFilterMeta>({});
const doNothing = () => {};

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
  store.settings.video_feed_model_img_size =
    camStore.data.video_feed_model_img_size;
  store.settings.video_feed_detect_mode = camStore.data.video_feed_detect_mode;
  store.settings.video_feed_confidence = isNumber(
    camStore.data.video_feed_confidence,
  )
    ? roundNumber(camStore.data.video_feed_confidence)
    : camStore.data.video_feed_confidence;
  store.settings.video_feed_object_detection =
    camStore.data.video_feed_object_detection;
  await camStore.updateCameraParams({
    video_feed_model_img_size: store.settings.video_feed_model_img_size,
    video_feed_detect_mode: store.settings.video_feed_detect_mode,
    video_feed_object_detection: store.settings.video_feed_object_detection,
    video_feed_confidence: store.settings.video_feed_confidence,
  });
}, 2000);

watch(
  () => selectedValue.value,
  async (newVal) => {
    const nextValue = Object.keys(newVal)[0] || null;
    camStore.data.video_feed_detect_mode = nextValue;
    await updateCameraParams();
    await camStore.fetchModels();
  },
);

watch(() => camStore.data.video_feed_detect_mode, updateCameraParams);
watch(() => camStore.data.video_feed_confidence, updateCameraParams);
watch(() => camStore.data.video_feed_object_detection, updateCameraParams);
onMounted(camStore.fetchModels);
</script>

<style scoped lang="scss">
.header {
  display: flex;
}
.title {
  font-weight: bold;
  font-family: var(--font-family);
  max-width: 75%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.flex {
  display: flex;
  gap: 10px;
}
.align-center {
  align-items: center;
}
.button-group {
  white-space: nowrap;
}
:deep(.p-inputtext) {
  width: 90px;
}
:deep(tr:hover) {
  cursor: pointer;
}
.search-wrapper {
  display: flex;
  flex: auto;
  justify-content: flex-end;
}

:deep(.p-fileupload-basic) {
  margin: 2rem 0;
}
</style>
