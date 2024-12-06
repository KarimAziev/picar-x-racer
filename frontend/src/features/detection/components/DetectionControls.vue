<template>
  <div :class="class" class="wrapper">
    <div class="p-field">
      <div class="flex-column">
        <ToggleSwitchField
          label="Detection"
          layout="row"
          field="toggle_detection"
          v-tooltip="'Toggle Object Detection'"
          :loading="detectionStore.loading"
          @update:model-value="updateDebounced"
          v-model="fields.active"
        />
        <TreeSelect
          inputId="model"
          v-model="fields.model"
          :options="nodes"
          placeholder="Model"
          filter
          :loading="detectionStore.loading"
          @before-show="handleSelectBeforeShow"
          @before-hide="handleSelectBeforeHide"
          @update:model-value="updateDebounced"
        >
          <template #dropdownicon>
            <i class="pi pi-search" />
          </template>
          <template #header>
            <div class="title">Available Models</div>
          </template>
          <template #footer>
            <div>
              <FileUpload
                mode="basic"
                name="model[]"
                url="/api/files/upload/data"
                @upload="detectionStore.fetchModels"
                :auto="true"
                chooseLabel="Add"
              />
            </div>
          </template>
        </TreeSelect>
      </div>
    </div>

    <div class="flex">
      <SelectField
        inputId="img_size"
        v-model="fields.img_size"
        placeholder="Img size"
        label="Img size"
        filter
        simple-options
        :loading="detectionStore.loading"
        @before-show="handleSelectBeforeShow"
        @before-hide="handleSelectBeforeHide"
        @update:model-value="updateDebounced"
        :options="imgSizeOptions"
      />
      <NumberField
        @keydown.stop="doNothing"
        @keyup.stop="doNothing"
        @keypress.stop="doNothing"
        field="confidence"
        label="Confidence"
        v-model="fields.confidence"
        :loading="detectionStore.loading"
        :min="0.1"
        :max="1.0"
        :step="0.1"
        @update:model-value="updateDebounced"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useSettingsStore } from "@/features/settings/stores";
import { useDetectionStore } from "@/features/detection";
import NumberField from "@/ui/NumberField.vue";
import { NONE_KEY, imgSizeOptions } from "@/features/settings/config";
import { useDetectionFields } from "@/features/detection";
import SelectField from "@/ui/SelectField.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";

defineProps<{ class?: string; label?: string }>();

const doNothing = () => {};
const detectionStore = useDetectionStore();

const store = useSettingsStore();
const { fields, updateDebounced } = useDetectionFields();

const handleSelectBeforeShow = () => {
  store.inhibitKeyHandling = true;
};

const handleSelectBeforeHide = () => {
  store.inhibitKeyHandling = false;
};

const nodes = computed(() => [
  { key: NONE_KEY, label: "None", selectable: true },
  ...detectionStore.detectors,
]);
</script>
<style scoped lang="scss">
@import "src/ui/field.scss";
.wrapper {
  max-width: 160px;
}
.p-field {
  margin: 0rem 0rem;
  max-width: 160px;
}
.label {
  font-weight: bold;
  position: relative;
  display: flex;
  flex-direction: column;
}

.wrapper {
  display: flex;
  flex-direction: column;
}
.flex {
  display: flex;
  align-items: center;
}
.flex-column {
  display: flex;
  flex-direction: column;
  text-align: left;
  gap: 5px;
}
:deep(.p-inputtext) {
  width: 90px;
}
.bold {
  font-weight: bold;
  text-align: left;
}

:deep(.p-treeselect) {
  height: 35px;
  display: flex;
  align-items: center;
}
</style>
