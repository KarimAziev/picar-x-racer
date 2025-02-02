<template>
  <div :class="class" class="flex md:max-w-56 flex-wrap gap-x-2">
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

      <TreeSelect
        class="w-[108px] md:w-[126px] xl:w-[148px]"
        inputId="model"
        v-model="fields.model"
        :options="nodes"
        placeholder="Model"
        tooltip="Object detection model '%s'"
        filter
        :disabled="detectionStore.loading"
        @before-show="handleSelectBeforeShow"
        @before-hide="handleSelectBeforeHide"
        @hide="focusToKeyboardHandler"
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
    </div>
    <SelectField
      fieldClassName="w-20"
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
      fieldClassName="w-20"
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
      fieldClassName="w-20"
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

import ModelUpload from "@/features/detection/components/ModelUpload.vue";
import { roundToOneDecimalPlace } from "@/util/number";
import Field from "@/ui/Field.vue";
import { focusToKeyboardHandler } from "@/features/controller/util";

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
