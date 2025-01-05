<template>
  <div class="flex items-center">
    <div
      class="font-bold max-w-[75%] whitespace-nowrap overflow-hidden text-ellipsis"
    >
      Current model: &nbsp;{{ detectionStore.data.model || "None" }}
    </div>
    <div class="flex flex-auto justify-end">
      <div class="search-field">
        <InputText
          class="max-w-20"
          id="search-models"
          v-model="filters['name'] as string"
          :pt="{ pcInput: { id: 'search-models' } }"
          placeholder="Search"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import InputText from "primevue/inputtext";
import type { TreeTableFilterMeta } from "primevue/treetable";
import type { DetectionFields } from "@/features/detection/composables/useDetectionFields";
import { useDetectionStore } from "@/features/detection";
import { inject } from "vue";

const fields = inject<DetectionFields["fields"]>("fields");
const filters = inject<TreeTableFilterMeta>("filters");

const detectionStore = useDetectionStore();

if (!fields || !filters) {
  throw new Error("fields and filters must be provided!");
}
</script>
