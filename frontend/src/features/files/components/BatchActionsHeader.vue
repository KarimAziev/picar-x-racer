<template>
  <div>Act on {{ markedFilenames.length }} files</div>
  <ButtonGroup>
    <Button
      label="Download"
      @click="handleDownloadMarked"
      :disabled="batchButtonsDisabled"
      severity="secondary"
      icon="pi pi-download"
    ></Button>
    <Button
      label="Download archive"
      @click="handleDownloadArchive"
      :disabled="batchButtonsDisabled"
      severity="secondary"
      icon="pi pi-download"
    ></Button>
    <Button
      severity="danger"
      :disabled="batchButtonsDisabled"
      @click="handleRemoveMarked"
      label="Delete"
      icon="pi pi-trash"
    ></Button>
    <Button
      severity="contrast"
      :disabled="batchButtonsDisabled || isDirChooseOpen"
      @click="openDirectoryChooserPopup"
      label="Move"
      icon="pi pi-arrows-alt"
    ></Button>
    <slot></slot>
  </ButtonGroup>
</template>

<script setup lang="ts">
import { computed, inject, Ref, ComputedRef } from "vue";
import { usePopupStore } from "@/features/settings/stores";
import { omit } from "@/util/obj";
import { isEmpty } from "@/util/guards";

const props = defineProps<{
  directories?: Record<string, boolean>;
  loadingRows?: Record<string, boolean>;
}>();

const expandedNodes = inject<Ref<Set<string>>>("expandedNodes");
const markedNodes = inject<Ref<Record<string, boolean>>>("markedNodes");
const markedFilenames = inject<ComputedRef<string[]>>("markedFilenames");
const isDirChooseOpen = defineModel<boolean>("directoryChooserVisible");

if (!expandedNodes || !markedNodes || !markedFilenames) {
  throw new Error("Expanded nodes and marked nodes must be provided!");
}

const popupStore = usePopupStore();
const emit = defineEmits([
  "download:file",
  "download-batch:archive",
  "remove:batch",
  "show:directory-chooser",
]);

const batchButtonsDisabled = computed(
  () =>
    isEmpty(markedFilenames.value) ||
    (props.loadingRows && !isEmpty(props.loadingRows)),
);

const handleRemoveMarked = () => {
  const filenames = markedFilenames.value;
  emit("remove:batch", filenames);
  markedNodes.value = omit(filenames, markedNodes.value);
};

const openDirectoryChooserPopup = () => {
  popupStore.isEscapable = false;
  isDirChooseOpen.value = true;
  emit("show:directory-chooser");
};

const handleDownloadMarked = () => {
  const filenames = markedFilenames.value;
  const directories: string[] = [];
  for (let i = 0; i < filenames.length; i++) {
    const file = filenames[i];
    if (props.directories && props.directories[file]) {
      directories.push(file);
    } else {
      emit("download:file", filenames[i]);
    }
  }
  if (directories.length > 0) {
    emit("download-batch:archive", directories);
  }
};

const handleDownloadArchive = () => {
  const filenames = markedFilenames.value;
  emit("download-batch:archive", filenames);
};
</script>
