<template>
  <div class="flex md:max-w-56 flex-wrap gap-x-1">
    <div>
      <Field label="Detection" layout="row">
        <button
          class="px-2 py-0 border border-transparent rounded-md bg-transparent transition-opacity duration-300 ease-in-out hover:bg-button-text-primary-hover-background focus:opacity-70 focus:outline-none focus:ring-2 focus:ring-current font-bold"
          v-tooltip="'Toggle Object Detection'"
          :disabled="detectionStore.loading || !detectionStore.data.model"
          @click="
            async () => {
              fields.active = !fields.active;
              await updateDebounced();
            }
          "
        >
          {{ fields.active ? "ON" : "OFF" }}
        </button>
      </Field>

      <ModelSelect class="w-48" />
    </div>
    <SelectField
      fieldClassName="w-24"
      inputId="img_size"
      v-model="fields.img_size"
      placeholder="Img size"
      label="Img size"
      filter
      :disabled="detectionStore.loading"
      @before-show="handleSelectBeforeShow"
      @before-hide="handleSelectBeforeHide"
      @hide="focusToKeyboardHandler"
      @update:model-value="updateDebounced"
      :options="imgSizeOptions"
    />
    <NumberField
      fieldClassName="w-24"
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
      inputClassName="w-24"
      @keydown.stop="doNothing"
      @keyup.stop="doNothing"
      @keypress.stop="doNothing"
      :normalizeValue="roundToTwoDecimalPlaces"
      field="iou_threshold"
      label="IoU"
      :editable="!isMobile"
      v-model="fields.iou_threshold"
      :disabled="detectionStore.loading"
      :min="0"
      :max="1"
      :step="0.05"
      tooltipHelp="Non-maximum suppression overlap threshold. Lower values remove more overlapping boxes; higher values retain more. Hailo models ignore this because NMS is compiled into the model."
      @update:model-value="updateDebounced"
    />
    <NumberField
      inputClassName="w-24"
      @keydown.stop="doNothing"
      @keyup.stop="doNothing"
      @keypress.stop="doNothing"
      field="max_detections"
      :editable="!isMobile"
      label="Max det."
      v-model="fields.max_detections"
      :disabled="detectionStore.loading"
      :min="1"
      :max="10000"
      :step="1"
      tooltipHelp="Maximum number of detections returned for each image after non-maximum suppression. Hailo models ignore this because their output count is fixed."
      @update:model-value="updateDebounced"
    />
    <NumberField
      inputClassName="w-24"
      @keydown.stop="doNothing"
      @keyup.stop="doNothing"
      @keypress.stop="doNothing"
      :normalizeValue="roundToTwoDecimalPlaces"
      :editable="!isMobile"
      v-tooltip="'Minimum confidence required to draw a pose keypoint.'"
      field="keypoint_confidence_threshold"
      label="Pose conf."
      v-model="fields.keypoint_confidence_threshold"
      :disabled="detectionStore.loading"
      :min="0"
      :max="1"
      :step="0.0001"
      @update:model-value="updateDebounced"
    />
    <NumberField
      inputClassName="w-24"
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
      :editable="!isMobile"
      :disabled="detectionStore.loading"
      :min="0.1"
      :max="10.0"
      :step="0.1"
      @update:model-value="updateDebounced"
    />
    <SelectField
      fieldClassName="w-24"
      :filter="false"
      inputId="overlay_style"
      v-model="fields.overlay_style"
      label="Style"
      :disabled="detectionStore.loading"
      @update:model-value="updateDebounced"
      :options="overlayStyleOptions"
      @before-show="handleSelectBeforeShow"
      @before-hide="handleSelectBeforeHide"
      @hide="focusToKeyboardHandler"
    />
    <ChipField
      fieldClassName="w-24"
      inputClass="max-w-24!"
      label="Labels"
      field="labels"
      v-model="fields.labels"
      :suggestions="fields.available_labels"
      :disabled="detectionStore.loading"
      tooltipHelp="Labels to include. Leave empty to detect every model label."
      @update:model-value="updateDebounced"
    />
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import { useDetectionStore } from "@/features/detection";
import NumberField from "@/ui/NumberField.vue";
import {
  imgSizeOptions,
  overlayStyleOptions,
} from "@/features/settings/config";
import { useDetectionFields } from "@/features/detection";
import SelectField from "@/ui/SelectField.vue";
import ChipField from "@/ui/ChipField.vue";

import { roundToOneDecimalPlace, roundToTwoDecimalPlaces } from "@/util/number";
import Field from "@/ui/Field.vue";
import { focusToKeyboardHandler } from "@/features/controller/util";
import ModelSelect from "@/features/detection/components/ModelSelect.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";

const isMobile = useDeviceWatcher();

const doNothing = () => {};

const detectionStore = useDetectionStore();

const settingsStore = useSettingsStore();

const { fields, updateDebounced } = useDetectionFields();

const handleSelectBeforeShow = () => {
  settingsStore.inhibitKeyHandling = true;
};

const handleSelectBeforeHide = () => {
  settingsStore.inhibitKeyHandling = false;
};
</script>
