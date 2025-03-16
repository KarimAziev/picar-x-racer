<template>
  <FilesTree
    :uploadURL="uploadURL"
    :store="store"
    list-class="h-[350px]"
    rowClass="grid grid-cols-[4%_10%_10%_30%_15%_15%_20%] gap-y-2 items-center h-[50px] hover:bg-mask relative"
  >
    <template #checkbox="{ path, is_dir }">
      <CheckboxCell :path="path" class="justify-between gap-4">
        <RadioButton
          :disabled="!isSelectableModel(path, is_dir)"
          @update:modelValue="handleUpdateModel"
          v-model="detectionStore.data.model"
          v-tooltip="'Select a model as default'"
          :inputId="`model-${path}`"
          :name="`model-${path}`"
          :value="path"
        />
      </CheckboxCell>
    </template>
  </FilesTree>
</template>

<script setup lang="ts">
import { inject, computed } from "vue";
import FilesTree from "@/features/files/components/FilesTree.vue";
import { makeUploadURL } from "@/features/files/api";
import { useDataStore } from "@/features/files/stores";
import { useStore as useDetectionStore } from "@/features/detection/store";
import { isSelectableModel } from "@/features/settings/util";
import type { DetectionFields } from "@/features/detection/composables/useDetectionFields";
import { normalizeValue } from "@/features/detection/composables/useDetectionFields";
import CheckboxCell from "@/features/files/components/Cells/CheckboxCell.vue";

const store = useDataStore();

const uploadURL = computed(() => makeUploadURL(store.mediaType));

const fields = inject<DetectionFields["fields"]>("fields");
const updateData = inject<DetectionFields["updateData"]>("updateData");

const detectionStore = useDetectionStore();

if (!fields || !updateData || !detectionStore) {
  throw new Error("fields, updateData, and detectionStore must be provided!");
}

const handleUpdateModel = (newValue: string) => {
  fields.model = normalizeValue(newValue);
  updateData();
};
</script>
