<template>
  <Field label="Object Detecton Model">
    <TreeSelect
      inputId="video_feed_detect_mode"
      v-model="selectedValue"
      :options="nodes"
      placeholder="Model"
      filter
      :loading="camStore.loadingData.video_feed_detect_mode"
      @before-show="handleSelectBeforeShow"
      @before-hide="handleSelectBeforeHide"
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
  </Field>
</template>

<script setup lang="ts">
import TreeSelect from "primevue/treeselect";
import { onMounted, ref, watch, computed } from "vue";

import { useCameraStore, useSettingsStore } from "@/features/settings/stores";
import Field from "@/ui/Field.vue";

const store = useSettingsStore();
const camStore = useCameraStore();
const handleSelectBeforeShow = () => {
  store.inhibitKeyHandling = true;
};

const handleSelectBeforeHide = () => {
  store.inhibitKeyHandling = false;
};

const NONE_KEY = "NONE";
const nodes = computed(() => [
  { key: NONE_KEY, label: "None", selectable: true },
  ...camStore.detectors,
]);
const selectedValue = ref(
  store.settings.video_feed_detect_mode
    ? { [store.settings.video_feed_detect_mode]: true }
    : {},
);

watch(
  () => selectedValue.value,
  async (newVal) => {
    const nextValue = Object.keys(newVal)[0] || null;
    store.settings.video_feed_detect_mode =
      nextValue === NONE_KEY ? null : nextValue;
    await camStore.updateCameraParams({
      video_feed_detect_mode: store.settings.video_feed_detect_mode,
    });
    await camStore.fetchModels();
  },
);

onMounted(async () => {
  await camStore.fetchModels();
});
</script>
