<template>
  <ModelFieldSet
    :imgSizeOptions="imgSizeOptions"
    :overlayStyleOptions="overlayStyleOptions"
    :loading="loading"
  />
  <ModelsTable />
</template>

<script setup lang="ts">
import { computed, provide } from "vue";
import { useDetectionStore } from "@/features/detection";
import { useSettingsStore } from "@/features/settings/stores";
import { useDetectionFields } from "@/features/detection";
import {
  imgSizeOptions,
  overlayStyleOptions,
} from "@/features/settings/config";
import ModelFieldSet from "@/features/settings/components/detection/ModelFieldSet.vue";
import ModelsTable from "@/features/settings/components/detection/ModelsTable.vue";

const settingsStore = useSettingsStore();
const detectionStore = useDetectionStore();

const { fields, updateDebounced, updateData } = useDetectionFields({
  store: detectionStore,
});

const loading = computed(() => detectionStore.loading || settingsStore.loading);

provide("fields", fields);
provide("updateDebounced", updateDebounced);
provide("updateData", updateData);
</script>
