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
      <div class="flex align-items-center">
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

      <FieldSet toggleable legend="Model parameters">
        <div class="flex gap-10 flex-wrap">
          <ToggleSwitchField
            label="Detection"
            class="align-items-center"
            field="settings.detection.active"
            @update:model-value="updateDebounced"
            v-tooltip="'Toggle object detection'"
            v-model="fields.active"
          />
          <SelectField
            inputId="settings.detection.img_size"
            v-model="fields.img_size"
            placeholder="Image size"
            label="Image size"
            filter
            simple-options
            v-tooltip="'The image size for the detection process'"
            :loading="loading"
            @update:model-value="updateDebounced"
            :options="imgSizeOptions"
          />
          <NumberField
            @keydown.stop="doNothing"
            @keyup.stop="doNothing"
            @keypress.stop="doNothing"
            field="settings.detection.confidence"
            label="Confidence"
            @update:model-value="updateDebounced"
            v-model="fields.confidence"
            v-tooltip="'The confidence threshold for detections'"
            :loading="loading"
            :min="0.1"
            :max="1.0"
            :step="0.1"
          />
          <NumberField
            @keydown.stop="doNothing"
            @keyup.stop="doNothing"
            @keypress.stop="doNothing"
            v-tooltip="
              'The maximum allowable time difference (in seconds) between the frame timestamp and the detection timestamp for overlay drawing to occur.'
            "
            field="settings.detection.overlay_draw_threshold"
            label="Overlay Threshold"
            v-model="fields.overlay_draw_threshold"
            :loading="detectionStore.loading"
            :min="0.1"
            :max="10.0"
            :step="0.1"
            @update:model-value="updateDebounced"
          />
          <ChipField
            label="Labels"
            field="settings.detection.labels"
            v-model="fields.labels"
            v-tooltip="
              'A list of labels to filter for specific object detections'
            "
            @update:model-value="updateDebounced"
          />
        </div>
      </FieldSet>
      <div>Click on the row to select the model</div>
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
  <ModelUpload />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import ButtonGroup from "primevue/buttongroup";
import TreeTable, { TreeTableFilterMeta } from "primevue/treetable";
import InputIcon from "primevue/inputicon";
import IconField from "primevue/iconfield";
import FieldSet from "primevue/fieldset";
import NumberField from "@/ui/NumberField.vue";
import { useMessagerStore } from "@/features/messager";
import { useDetectionStore } from "@/features/detection";
import { downloadFile, removeFile } from "@/features/settings/api";
import { useSettingsStore } from "@/features/settings/stores";
import { useDetectionFields } from "@/features/detection";
import { imgSizeOptions } from "@/features/settings/config";
import SelectField from "@/ui/SelectField.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import ChipField from "@/ui/ChipField.vue";
import ModelUpload from "@/features/detection/components/ModelUpload.vue";

const store = useSettingsStore();
const detectionStore = useDetectionStore();
const { fields, updateDebounced } = useDetectionFields({
  store: detectionStore,
});

const items = computed(() => detectionStore.detectors);
const filters = ref<TreeTableFilterMeta>({});
const doNothing = () => {};
const messager = useMessagerStore();

const loading = computed(() => detectionStore.loading || store.loading);

const handleRemove = async (key: string) => {
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
  store.data.detection = detectionStore.data;
});
</script>

<style scoped lang="scss">
.title {
  font-weight: bold;
  font-family: var(--font-family);
  max-width: 75%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
</style>
