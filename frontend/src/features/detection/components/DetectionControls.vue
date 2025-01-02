<template>
  <div class="flex max-w-52 flex-wrap gap-x-1">
    <ToggleSwitchField
      fieldClassName="my-0"
      label="Detection"
      layout="row"
      field="toggle_detection"
      v-tooltip="'Toggle Object Detection'"
      :disabled="detectionStore.loading || !detectionStore.data.model"
      @update:model-value="updateDebounced"
      v-model="fields.active"
    />
    <TreeSelect
      inputId="model"
      v-model="fields.model"
      :options="nodes"
      placeholder="Model"
      tooltip="Object detection model '%s'"
      filter
      :disabled="detectionStore.loading"
      @before-show="handleSelectBeforeShow"
      @before-hide="handleSelectBeforeHide"
      @update:model-value="updateDebounced"
    >
      <template #dropdownicon>
        <i class="pi pi-angle-down pr-2 pt-1 md:pt-1.5" />
      </template>
      <template #header>
        <div class="p-2">Available Models</div>
      </template>
      <template #footer>
        <ModelUpload />
      </template>
    </TreeSelect>
    <SelectField
      fieldClassName="my-0 w-20"
      inputId="img_size"
      v-model="fields.img_size"
      placeholder="Img size"
      label="Img size"
      filter
      :disabled="detectionStore.loading"
      @before-show="handleSelectBeforeShow"
      @before-hide="handleSelectBeforeHide"
      @update:model-value="updateDebounced"
      :options="imgSizeOptions"
    />
    <NumberField
      fieldClassName="my-0 w-20"
      @keydown.stop="doNothing"
      @keyup.stop="doNothing"
      @keypress.stop="doNothing"
      :normalizeValue="roundToOneDecimalPlace"
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
      fieldClassName="my-0"
      @keydown.stop="doNothing"
      :normalizeValue="roundToOneDecimalPlace"
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
    <SelectField
      fieldClassName="my-0 w-20"
      :filter="false"
      inputId="overlay_style"
      v-model="fields.overlay_style"
      label="Style"
      :disabled="detectionStore.loading"
      @update:model-value="updateDebounced"
      :options="overlayStyleOptions"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useSettingsStore } from "@/features/settings/stores";
import { useDetectionStore } from "@/features/detection";
import NumberField from "@/ui/NumberField.vue";
import {
  imgSizeOptions,
  overlayStyleOptions,
} from "@/features/settings/config";
import { useDetectionFields } from "@/features/detection";
import SelectField from "@/ui/SelectField.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import ModelUpload from "@/features/detection/components/ModelUpload.vue";
import { roundToOneDecimalPlace } from "@/util/number";

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
    max-width: 150px;
  }
}
</style>
