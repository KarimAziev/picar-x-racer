<template>
  <div :class="class" class="wrapper">
    <div class="p-field">
      <div class="flex-column">
        <div class="flex">
          Detection:
          <ToggleSwitch
            inputId="toggle_detection"
            v-tooltip="'Toggle Object Detection'"
            :loading="detectionStore.loading"
            @update:model-value="updateCameraParams"
            v-model="detectionStore.data.active"
          />
        </div>
        <TreeSelect
          inputId="model"
          v-model="selectedValue"
          :options="nodes"
          placeholder="Model"
          filter
          :loading="detectionStore.loading"
          @before-show="handleSelectBeforeShow"
          @before-hide="handleSelectBeforeHide"
          @update:model-value="updateCameraParams"
        >
          <template #dropdownicon>
            <i class="pi pi-search" />
          </template>
          <template #header>
            <div class="font-medium px-3 py-2">Available Models</div>
          </template>
          <template #footer>
            <div>
              <FileUpload
                mode="basic"
                name="model[]"
                url="/api/upload/data"
                @upload="detectionStore.fetchModels"
                :auto="true"
                chooseLabel="Add"
              />
            </div>
          </template>
        </TreeSelect>
      </div>
    </div>
    Models paramaters
    <div class="flex">
      <NumberField
        @keydown.stop="doThis"
        @keyup.stop="doThis"
        @keypress.stop="doThis"
        showButtons
        label="Img size"
        field="img_size"
        :loading="detectionStore.loading"
        v-model="detectionStore.data.img_size"
        :step="10"
        @update:model-value="updateCameraParams"
      />
      <NumberField
        @keydown.stop="doThis"
        @keyup.stop="doThis"
        @keypress.stop="doThis"
        field="confidence"
        label="Confidence"
        v-model="detectionStore.data.confidence"
        :loading="detectionStore.loading"
        :min="0.1"
        :max="1.0"
        :step="0.1"
        @update:model-value="updateCameraParams"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import ToggleSwitch from "primevue/toggleswitch";
import {
  useSettingsStore,
  useDetectionStore,
} from "@/features/settings/stores";
import { useAsyncDebounce } from "@/composables/useDebounce";
import NumberField from "@/ui/NumberField.vue";
import { NONE_KEY } from "@/features/settings/config";
import { roundNumber } from "@/util/number";
import { isNumber } from "@/util/guards";

defineProps<{ class?: string; label?: string }>();

const doThis = () => {};
const detectionStore = useDetectionStore();

const store = useSettingsStore();
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
const selectedValue = ref(
  detectionStore.data.model ? { [detectionStore.data.model]: true } : {},
);

const updateCameraParams = useAsyncDebounce(async () => {
  const nextModel = Object.keys(selectedValue.value)[0] || null;
  await detectionStore.updateData({
    img_size: detectionStore.data.img_size,
    model: nextModel,
    active: detectionStore.data.active,
    confidence: isNumber(detectionStore.data.confidence)
      ? roundNumber(detectionStore.data.confidence, 1)
      : detectionStore.data.confidence,
  });
  await detectionStore.fetchModels();
}, 3000);

onMounted(detectionStore.fetchModels);
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
}
:deep(.p-inputtext) {
  width: 90px;
}
.bold {
  font-weight: bold;
  text-align: left;
}
</style>
