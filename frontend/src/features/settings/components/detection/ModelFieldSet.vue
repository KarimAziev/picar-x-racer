<template>
  <FieldSet toggleable legend="Model parameters">
    <div class="flex gap-2.5 flex-wrap">
      <ToggleSwitchField
        fieldClassName="items-center gap-2"
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
        fieldClassName="w-20"
        :filter="false"
        inputId="settings.detection.overlay_style"
        v-model="fields.overlay_style"
        label="Style"
        tooltipHelp="Style of bounding boxes"
        :loading="loading"
        @update:model-value="updateDebounced"
        :options="overlayStyleOptions"
      />
      <ChipField
        label="Labels"
        field="settings.detection.labels"
        v-model="fields.labels"
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
import { useDetectionStore, OverlayStyle } from "@/features/detection";
import { ValueLabelOption } from "@/features/settings/interface";
import NumberField from "@/ui/NumberField.vue";
import SelectField from "@/ui/SelectField.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import ChipField from "@/ui/ChipField.vue";
import { roundToOneDecimalPlace } from "@/util/number";

const detectionStore = useDetectionStore();
const fields = inject<DetectionFields["fields"]>("fields");
const updateDebounced =
  inject<DetectionFields["updateDebounced"]>("updateDebounced");

defineProps<{
  imgSizeOptions?: ValueLabelOption<number>[];
  overlayStyleOptions: ValueLabelOption<OverlayStyle>[];
  loading?: boolean;
}>();

if (!fields) {
  throw new Error("fields must be provided!");
}
</script>
