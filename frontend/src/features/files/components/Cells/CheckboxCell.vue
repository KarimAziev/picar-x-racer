<template>
  <Cell>
    <slot></slot>
    <Checkbox
      v-model="markedNodes[path]"
      :inputId="`${[path]}-check`"
      :disabled="isUploadingRow"
      binary
      @update:model-value="toggleMarked"
    />
  </Cell>
</template>

<script setup lang="ts">
import { inject, computed, Ref } from "vue";
import { isNumber } from "@/util/guards";
import type { UploadingFileDetail } from "@/features/files/interface";
import Cell from "@/features/files/components/Cell.vue";

export interface Props extends Pick<UploadingFileDetail, "path" | "progress"> {}
const props = defineProps<Props>();

const markedNodes = inject<Ref<Record<string, boolean>>>("markedNodes");
const isUploadingRow = computed(() => isNumber(props.progress));

const emit = defineEmits(["toggle:checked"]);

const toggleMarked = () => {
  emit("toggle:checked", props.path);
};
</script>
