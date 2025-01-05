<template>
  <div>
    <Header />
    <ModelFieldSet
      :imgSizeOptions="imgSizeOptions"
      :overlayStyleOptions="overlayStyleOptions"
      :loading="loading"
    />
    <ModelsTable />
  </div>
  <ModelUpload />
</template>

<script setup lang="ts">
import { ref, computed, provide, defineAsyncComponent } from "vue";
import type { TreeTableFilterMeta } from "primevue/treetable";
import { useDetectionStore } from "@/features/detection";
import { useSettingsStore } from "@/features/settings/stores";
import { useDetectionFields } from "@/features/detection";
import {
  imgSizeOptions,
  overlayStyleOptions,
} from "@/features/settings/config";
import ModelUpload from "@/features/detection/components/ModelUpload.vue";
import Header from "@/features/settings/components/detection/Header.vue";
import Skeleton from "@/ui/Skeleton.vue";
import ErrorComponent from "@/ui/ErrorComponent.vue";
import ModelFieldSet from "@/features/settings/components/detection/ModelFieldSet.vue";

const ModelsTable = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/detection/ModelsTable.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const settingsStore = useSettingsStore();
const detectionStore = useDetectionStore();
const { fields, updateDebounced } = useDetectionFields({
  store: detectionStore,
});

const filters = ref<TreeTableFilterMeta>({});

const loading = computed(() => detectionStore.loading || settingsStore.loading);

provide("fields", fields);
provide("updateDebounced", updateDebounced);
provide("filters", filters);
</script>
