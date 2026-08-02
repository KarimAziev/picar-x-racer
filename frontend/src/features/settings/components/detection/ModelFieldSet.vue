<template>
  <FieldSet toggleable legend="Model common parameters">
    <div class="grid grid-cols-2 gap-1">
      <ToggleSwitchField
        label="Detection"
        field="settings.detection.active"
        @update:model-value="updateDebounced"
        tooltipHelp="Toggle object detection"
        v-model="fields.active"
      />
      <SelectField
        fieldClassName="min-w-20"
        inputId="settings.detection.img_size"
        v-model="fields.img_size"
        placeholder="Image size"
        label="Image size"
        filter
        tooltipHelp="The image size for the detection process"
        :loading="loading"
        @update:model-value="updateDebounced"
        :options="imgSizeOptions"
      />
      <NumberField
        editable
        field="settings.detection.confidence"
        label="Confidence"
        :normalizeValue="roundToOneDecimalPlace"
        @update:model-value="updateDebounced"
        v-model="fields.confidence"
        tooltipHelp="The confidence threshold for detections"
        :loading="loading"
        :min="0.1"
        :max="1.0"
        :step="0.1"
      />
      <NumberField
        editable
        field="settings.detection.iou_threshold"
        label="IoU threshold"
        :normalizeValue="roundToTwoDecimalPlaces"
        @update:model-value="updateDebounced"
        v-model="fields.iou_threshold"
        tooltipHelp="Non-maximum suppression overlap threshold. Lower values remove more overlapping boxes, higher values retain more."
        :loading="loading"
        :min="0"
        :max="1"
        :step="0.05"
      />
      <NumberField
        editable
        field="settings.detection.max_detections"
        label="Max detections"
        @update:model-value="updateDebounced"
        v-model="fields.max_detections"
        tooltipHelp="Maximum number of detections returned for each image after non-maximum suppression."
        :loading="loading"
        :min="1"
        :max="10000"
        :step="1"
      />
      <NumberField
        editable
        :normalizeValue="roundToOneDecimalPlace"
        tooltipHelp="The maximum allowable time difference (in seconds) between the frame timestamp and the detection timestamp for overlay drawing to occur."
        field="settings.detection.overlay_draw_threshold"
        label="Threshold"
        v-model="fields.overlay_draw_threshold"
        :loading="detectionStore.loading"
        :min="0.1"
        :max="10.0"
        :step="0.1"
        @update:model-value="updateDebounced"
      />
      <SelectField
        :filter="false"
        inputId="settings.detection.overlay_style"
        v-model="fields.overlay_style"
        label="Style"
        tooltipHelp="Style of bounding boxes"
        :loading="loading"
        @update:model-value="updateDebounced"
        :options="overlayStyleOptions"
      />
      <NumberField
        editable
        field="settings.detection.keypoint_confidence_threshold"
        label="Pose confidence"
        :normalizeValue="roundToTwoDecimalPlaces"
        @update:model-value="updateDebounced"
        v-model="fields.keypoint_confidence_threshold"
        tooltipHelp="Minimum confidence required to draw an individual pose keypoint"
        :loading="loading"
        :min="0"
        :max="1"
        :step="0.001"
      />
      <SelectField
        :filter="false"
        inputId="settings.detection.segmentation_detail"
        v-model="fields.segmentation_detail"
        label="Detail"
        tooltipHelp="Segmentation overlay detail"
        :loading="loading"
        @update:model-value="updateDebounced"
        :options="segmentationDetailOptions"
      />
      <ChipField
        label="Labels"
        fluid
        field="settings.detection.labels"
        v-model="fields.labels"
        :suggestions="fields.available_labels"
        tooltipHelp="A list of labels to filter for specific object detections. Type label and press 'Enter'."
        @update:model-value="updateDebounced"
      />
    </div>
  </FieldSet>
</template>

<script setup lang="ts">
import { inject } from "vue";
import FieldSet from "primevue/fieldset";
import type { DetectionFields } from "@/features/detection/composables/useDetectionFields";
import {
  useDetectionStore,
  OverlayStyle,
  SegmentationDetail,
} from "@/features/detection";
import { ValueLabelOption } from "@/features/settings/interface";
import NumberField from "@/ui/NumberField.vue";
import SelectField from "@/ui/SelectField.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import ChipField from "@/ui/ChipField.vue";
import { roundToOneDecimalPlace, roundToTwoDecimalPlaces } from "@/util/number";

const detectionStore = useDetectionStore();
const fields = inject<DetectionFields["fields"]>("fields");
const updateDebounced =
  inject<DetectionFields["updateDebounced"]>("updateDebounced");

defineProps<{
  imgSizeOptions?: ValueLabelOption<number>[];
  overlayStyleOptions: ValueLabelOption<OverlayStyle>[];
  segmentationDetailOptions: ValueLabelOption<SegmentationDetail>[];
  loading?: boolean;
}>();

if (!fields) {
  throw new Error("fields must be provided!");
}
</script>
