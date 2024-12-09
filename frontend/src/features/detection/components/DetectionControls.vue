<template>
  <div :class="class" class="flex flex-col">
    <div class="p-field max-w-160">
      <div class="flex flex-col gap-5 text-align-left">
        <ToggleSwitchField
          fieldClassName="opacity-hover"
          label="Detection"
          layout="row"
          field="toggle_detection"
          v-tooltip="'Toggle Object Detection'"
          :disabled="detectionStore.loading || !detectionStore.data.model"
          @update:model-value="updateDebounced"
          v-model="fields.active"
        />
        <TreeSelect
          class="opacity-hover"
          inputId="model"
          v-model="fields.model"
          :options="nodes"
          placeholder="Model"
          filter
          :disabled="detectionStore.loading"
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
            <ModelUpload />
          </template>
        </TreeSelect>
      </div>
    </div>

    <div class="flex align-items-end gap-5 jc-around max-w-200">
      <SelectField
        fieldClassName="img-size opacity-hover"
        inputId="img_size"
        v-model="fields.img_size"
        placeholder="Img size"
        label="Img size"
        filter
        simple-options
        :disabled="detectionStore.loading"
        @before-show="handleSelectBeforeShow"
        @before-hide="handleSelectBeforeHide"
        @update:model-value="updateDebounced"
        :options="imgSizeOptions"
      />
      <NumberField
        fieldClassName="opacity-hover"
        @keydown.stop="doNothing"
        @keyup.stop="doNothing"
        @keypress.stop="doNothing"
        field="confidence"
        label="Confidence"
        v-model="fields.confidence"
        :disabled="detectionStore.loading"
        :min="0.1"
        :max="1.0"
        :step="0.1"
        @update:model-value="updateDebounced"
      />
      <NumberField
        fieldClassName="opacity-hover"
        @keydown.stop="doNothing"
        @keyup.stop="doNothing"
        @keypress.stop="doNothing"
        v-tooltip="
          'The maximum allowable time difference (in seconds) between the frame timestamp and the detection timestamp for overlay drawing to occur.'
        "
        field="overlay_draw_threshold"
        label="Threshold"
        v-model="fields.overlay_draw_threshold"
        :disabled="detectionStore.loading"
        :min="0.1"
        :max="10.0"
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
import { imgSizeOptions } from "@/features/settings/config";
import { useDetectionFields } from "@/features/detection";
import SelectField from "@/ui/SelectField.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import ModelUpload from "@/features/detection/components/ModelUpload.vue";

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

const nodes = computed(() => detectionStore.detectors);
</script>
<style scoped lang="scss">
@use "@/ui/field.scss";

.p-field {
  margin: 0rem 0rem;
}

.title {
  padding: 0.5rem;
}
.label {
  font-weight: bold;
  position: relative;
  display: flex;
  flex-direction: column;
}

:deep(.p-inputtext),
:deep(.img-size) {
  width: 70px;
}

:deep(.p-treeselect) {
  height: 30px;
  display: flex;
  align-items: center;
  width: 150px;
  @media (min-width: 576px) {
    max-width: 140px;
  }
  @media (min-width: 1200px) {
    height: 40px;
    max-width: 220px;
  }
}
</style>
