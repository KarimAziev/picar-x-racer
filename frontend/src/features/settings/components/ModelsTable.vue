<template>
  <TreeTable
    :rowHover="true"
    v-model:selectionKeys="fields.model"
    :value="items"
    :loading="loading"
    dataKey="key"
    :metaKeySelection="false"
    selectionMode="single"
    filterMode="lenient"
    :filters="filters"
    @update:selectionKeys="updateDebounced"
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
            @update:model-value="updateDebounced"
            v-tooltip="'Toggle object detection'"
            v-model="fields.active"
          />
        </Field>

        <SelectField
          inputId="img_size"
          v-model="fields.img_size"
          placeholder="Img size"
          label="Img size"
          filter
          simple-options
          :loading="loading"
          @update:model-value="updateDebounced"
          :options="imgSizeOptions"
        />
        <NumberField
          @keydown.stop="doNothing"
          @keyup.stop="doNothing"
          @keypress.stop="doNothing"
          field="confidence"
          label="Confidence"
          @update:model-value="updateDebounced"
          v-model="fields.confidence"
          :loading="loading"
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
import { ref, computed, onMounted } from "vue";
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

import Field from "@/ui/Field.vue";
import { useDetectionFields } from "@/features/settings/composable/useDetectionFields";
import { imgSizeOptions } from "@/features/settings/config";
import SelectField from "@/ui/SelectField.vue";

const store = useSettingsStore();
const detectionStore = useDetectionStore();
const { fields, updateDebounced } = useDetectionFields({
  store: detectionStore,
});

const loading = computed(() => detectionStore.loading || store.loading);

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

onMounted(() => {
  store.settings.detection = detectionStore.data;
});
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
