<template>
  <div :class="class" class="wrapper">
    <div class="p-field">
      <div class="flex-column">
        <div class="flex">
          Detection:
          <Button
            class="label"
            @click="
              () => {
                camStore.data.video_feed_object_detection =
                  !camStore.data.video_feed_object_detection;
                updateCameraParams();
              }
            "
            aria-label="Toggle object detection"
            text
            ><span class="bold">&nbsp;{{ toggleLabel }}</span>
          </Button>
        </div>
        <TreeSelect
          inputId="video_feed_detect_mode"
          v-model="selectedValue"
          :options="nodes"
          placeholder="Model"
          filter
          :loading="camStore.loadingData.video_feed_detect_mode"
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
                @upload="camStore.fetchModels"
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
        field="video_feed_model_img_size"
        :loading="camStore.loadingData.video_feed_model_img_size"
        v-model="camStore.data.video_feed_model_img_size"
        :step="10"
        @update:model-value="updateCameraParams"
      />
      <NumberField
        @keydown.stop="doThis"
        @keyup.stop="doThis"
        @keypress.stop="doThis"
        field="video_feed_confidence"
        label="Confidence"
        v-model="camStore.data.video_feed_confidence"
        :loading="camStore.loadingData.video_feed_confidence"
        :min="0.1"
        :max="1.0"
        :step="0.1"
        @update:model-value="updateCameraParams"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, computed } from "vue";
import { useCameraStore, useSettingsStore } from "@/features/settings/stores";
import { useAsyncDebounce } from "@/composables/useDebounce";
import NumberField from "@/ui/NumberField.vue";
import { NONE_KEY } from "@/features/settings/config";

defineProps<{ class?: string; label?: string }>();

const doThis = () => {};
const camStore = useCameraStore();

const store = useSettingsStore();
const handleSelectBeforeShow = () => {
  store.inhibitKeyHandling = true;
};

const toggleLabel = computed(() =>
  camStore.data.video_feed_object_detection ? "ON" : "OFF",
);

const handleSelectBeforeHide = () => {
  store.inhibitKeyHandling = false;
};

const nodes = computed(() => [
  { key: NONE_KEY, label: "None", selectable: true },
  ...camStore.detectors,
]);
const selectedValue = ref(
  store.settings.video_feed_detect_mode
    ? { [store.settings.video_feed_detect_mode]: true }
    : {},
);

const updateCameraParams = useAsyncDebounce(async () => {
  await camStore.updateCameraParams({
    video_feed_model_img_size: camStore.data.video_feed_model_img_size,
    video_feed_detect_mode: camStore.data.video_feed_detect_mode,
    video_feed_object_detection: camStore.data.video_feed_object_detection,
  });
  await camStore.fetchModels();
}, 2000);

watch(
  () => selectedValue.value,
  async (newVal) => {
    const nextValue = Object.keys(newVal)[0] || null;
    camStore.data.video_feed_detect_mode =
      nextValue === NONE_KEY ? null : nextValue;
    updateCameraParams();
  },
);

onMounted(camStore.fetchModels);
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
