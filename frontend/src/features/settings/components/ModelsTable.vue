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
          Current model: &nbsp;{{ detectionStore.data.model || "None" }}
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
            inputId="active"
            v-tooltip="'Toggle object detection'"
            v-model="detectionStore.data.active"
          />
        </Field>

        <NumberField
          @keydown.stop="doNothing"
          @keyup.stop="doNothing"
          @keypress.stop="doNothing"
          showButtons
          label="Img size"
          inputId="img_size"
          :loading="detectionStore.loadingData.img_size"
          v-model="detectionStore.data.img_size"
          :step="10"
        />
        <NumberField
          @keydown.stop="doNothing"
          @keyup.stop="doNothing"
          @keypress.stop="doNothing"
          field="confidence"
          label="Confidence"
          v-model="detectionStore.data.confidence"
          :loading="detectionStore.loadingData.confidence"
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
    @upload="detectionStore.fetchModels"
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
import {
  useSettingsStore,
  useDetectionStore,
} from "@/features/settings/stores";
import { useAsyncDebounce } from "@/composables/useDebounce";
import { roundNumber } from "@/util/number";
import { isNumber } from "@/util/guards";
import Field from "@/ui/Field.vue";

const store = useSettingsStore();
const detectionStore = useDetectionStore();
const loading = computed(() => detectionStore.loading);
const selectedValue = ref(
  store.settings.detection.model
    ? { [store.settings.detection.model]: true }
    : {},
);

const items = computed(() => detectionStore.detectors);
const filters = ref<TreeTableFilterMeta>({});
const doNothing = () => {};

const handleRemove = async (key: string) => {
  const messager = useMessagerStore();
  try {
    await removeFile("data", key);
    await detectionStore.fetchModels();
  } catch (error) {
    messager.handleError(error);
  }
};

const handleDownloadFile = (value: string) => {
  downloadFile("data", value);
};

const updateCameraParams = useAsyncDebounce(async () => {
  store.settings.detection.img_size = detectionStore.data.img_size;
  store.settings.detection.model = detectionStore.data.model;
  store.settings.detection.confidence = isNumber(detectionStore.data.confidence)
    ? roundNumber(detectionStore.data.confidence, 1)
    : detectionStore.data.confidence;
  store.settings.detection.active = detectionStore.data.active;

  await detectionStore.updateData({
    img_size: store.settings.detection.img_size,
    model: store.settings.detection.model,
    active: store.settings.detection.active,
    confidence: store.settings.detection.confidence,
  });
}, 2000);

watch(
  () => selectedValue.value,
  async (newVal) => {
    const nextValue = Object.keys(newVal)[0] || null;
    detectionStore.data.model = nextValue;
    await updateCameraParams();
    await detectionStore.fetchModels();
  },
);

onMounted(detectionStore.fetchModels);
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
