<template>
  <div class="w-[108px] md:w-[126px] xl:w-[148px]">
    <TreeSelect
      placeholder="Detection model"
      ref="treeSelectRef"
      :loading="detectionStore.loading"
      v-model:model-value="selectedModel"
      :nodes="dataStore.data as TreeNode[]"
      @update:model-value="handleUpdateModel"
      key-prop="path"
      label-prop="name"
      :selectable="(node) => isSelectableModel(node.path, node.is_dir)"
      :itemSize="40"
      :disabled="detectionStore.loading"
      @show="handleTreeSelectShow"
      @hide="
        () => {
          removeKeyEventListeners();
          focusToKeyboardHandler();
          if (dataStore.search.value && dataStore.search.value.length > 0) {
            dataStore.search.value = '';
            dataStore.fetchData();
          }
        }
      "
    >
      <template #header>
        <InputText
          ref="inputRef"
          autocomplete="off"
          @update:model-value="handleSearch"
          class="max-w-20"
          id="model-search"
          v-model="dataStore.search.value"
          :pt="{ pcInput: { id: 'model-search' } }"
          placeholder="Search"
        />
      </template>
      <template #footer>
        <ModelUpload />
      </template>
    </TreeSelect>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  onMounted,
  watch,
  useTemplateRef,
  ComponentPublicInstance,
  nextTick,
} from "vue";
import { useDetectionStore } from "@/features/detection";
import { useDetectionFields, normalizeValue } from "@/features/detection";

import ModelUpload from "@/features/detection/components/ModelUpload.vue";
import { focusToKeyboardHandler } from "@/features/controller/util";
import { useDetectionDataStore } from "@/features/files/stores";
import TreeSelect from "@/ui/TreeSelect.vue";
import type { TreeNode } from "@/types/tree";
import { findItemInTree } from "@/features/files/components/util";
import { GroupedFile } from "@/features/files/interface";
import { isSelectableModel } from "@/features/settings/util";
import { useAsyncDebounce } from "@/composables/useDebounce";
import { Nullable } from "@/util/ts-helpers";

import { formatKeyEventItem } from "@/util/keyboard-util";
import { omit } from "@/util/obj";

defineProps<{ class?: string; label?: string }>();

const treeSelectRef = useTemplateRef("treeSelectRef");
const dataStore = useDetectionDataStore();

const inputRef =
  ref<
    Nullable<ComponentPublicInstance<{}, any> & { $el: HTMLTextAreaElement }>
  >(null);

const detectionStore = useDetectionStore();

const findModel = () => {
  const found = findItemInTree(
    "path",
    detectionStore.data.model as keyof GroupedFile,
    dataStore.data,
  );

  return found || null;
};

const selectedModel = ref<TreeNode | null>(findModel());

const { fields, updateData } = useDetectionFields();

const handleUpdateModel = (node: TreeNode) => {
  fields.model = normalizeValue(node.path);
  selectedModel.value = node;
  updateData();
};

const addKeyEventListeners = () => {
  const inputEl = inputRef.value?.$el;
  if (inputEl) {
    inputEl?.addEventListener("keyup", handleInputKeyUp);
  }
  window.addEventListener("keyup", handleGlobalKeyUp);
};

const removeKeyEventListeners = () => {
  const inputEl = inputRef.value?.$el;
  if (inputEl) {
    inputEl?.removeEventListener("keyup", handleInputKeyUp);
  }
  window.removeEventListener("keyup", handleGlobalKeyUp);
};

const handleInputKeyUp = (event: Event) => {
  const key = formatKeyEventItem(event as KeyboardEvent);
  if (treeSelectRef.value?.keymap) {
    const kmap = omit(["Space"], treeSelectRef.value?.keymap);
    if (kmap[key]) {
      event.stopPropagation();
      event.preventDefault();
      kmap[key]();
    }
  }
};

const handleGlobalKeyUp = (event: KeyboardEvent) => {
  const key = formatKeyEventItem(event as KeyboardEvent);

  if (
    treeSelectRef.value?.keymap[key] ||
    event.ctrlKey ||
    (key.length > 1 && key !== "Backspace")
  ) {
    return;
  }

  const inputEl: HTMLInputElement = inputRef.value?.$el;
  if (inputEl && document.activeElement !== inputEl) {
    event.stopPropagation();
    event.preventDefault();
    inputEl?.focus();
    if (key === "Backspace") {
      const val = dataStore.search.value;
      if (val && val.length > 0) {
        dataStore.search.value = dataStore.search.value.substring(0, -1);
        handleSearch(dataStore.search.value);
      }
    } else {
      dataStore.search.value = `${dataStore.search.value}${event.key}`;
      handleSearch(dataStore.search.value);
      inputEl?.focus();
    }
  }
};

const handleTreeSelectShow = async () => {
  await nextTick();

  const inputEl = inputRef.value?.$el;
  if (inputEl) {
    inputEl?.focus();
    addKeyEventListeners();
  }
};

const handleSearch = useAsyncDebounce(async (value: string | undefined) => {
  await dataStore.fetchData();
  if (value && value.length > 0) {
    treeSelectRef.value?.expandAll();
  }
}, 500);

watch(
  () => [detectionStore.data.model, dataStore.data],
  () => {
    selectedModel.value = findModel();
  },
);

onMounted(dataStore.fetchData);
</script>
