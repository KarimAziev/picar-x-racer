<template>
  <Fieldset legend="Filters" toggleable>
    <div class="flex items-center gap-2 flex-wrap">
      <template
        v-for="(options, field) in store.filter_info"
        :key="`filter-${field}`"
      >
        <div class="flex flex-col" v-if="options && options?.length > 0">
          <div class="font-bold">By&nbsp;{{ startCase(field) }}:</div>
          <MultiSelect
            :maxSelectedLabels="1"
            :selectedItemsLabel="`${store.filters[field] && store.filters[field]?.value && store.filters[field]?.value.length} items`"
            :pt="{
              input: {
                id: `filter-id-${field}`,
                name: `filter-name-${field}`,
              },
            }"
            :options="options"
            class="w-38"
            optionLabel="label"
            optionValue="value"
            :placeholder="`${startCase(field)} filter`"
            v-model:model-value="store.filters[field].value"
            @update:model-value="store.fetchData"
          >
            <template #dropdownicon>
              <i class="pi pi-angle-down" />
            </template>
          </MultiSelect>
        </div>
      </template>
      <div class="flex gap-2 justify-end flex-auto text-right">
        <Button
          severity="contrast"
          outlined
          @click="store.fetchData"
          label="Refresh"
          icon="pi pi-refresh"
        ></Button>
        <Button
          severity="info"
          :disabled="!store.hasFilters"
          @click="store.resetFilters"
          label="Reset filters"
          icon="pi pi-reset"
        ></Button>
      </div>
    </div>
  </Fieldset>
  <div class="flex flex-col gap-2 mb-2">
    <BatchActionsHeader
      :loadingRows="loadingRows"
      :directories="dirs"
      v-model:directory-chooser-visible="isDirChooseOpen"
      @download:file="store.downloadFile"
      @download-batch:archive="store.downloadFilesArchive"
      @remove:batch="store.batchRemoveFiles"
    />
  </div>

  <ButtonGroup>
    <Button
      severity="secondary"
      @click="openCreateDirectoryPopup"
      label="New directory"
      icon="pi pi-folder-plus"
    ></Button>
    <Button
      severity="secondary"
      @click="
        () => {
          textFilePopupVisible = true;
        }
      "
      label="New text file"
      icon="pi pi-plus"
    ></Button>
    <Uploader
      v-if="uploadURL"
      ref="uploaderRef"
      :url="uploadURL"
      :store="store"
    />
  </ButtonGroup>

  <div class="flex items-center">
    <div class="flex flex-auto justify-end gap-2">
      <div class="search-field">
        <InputText
          @update:model-value="handleSearch"
          class="max-w-20"
          autocomplete="off"
          id="search-model-table"
          v-model="store.search.value"
          :pt="{ pcInput: { id: 'search-model-table' } }"
          placeholder="Search"
        />
      </div>
    </div>
  </div>

  <Breadcrumb :home="breadcrumbHome" :model="breadcrumbItems">
    <template #item="{ item }">
      <ButtonIcon
        :disabled="store.dir === item.value"
        :icon="item.icon"
        text
        class="font-bold"
        @click="handleUpdateDir(item.value)"
      >
        <span class="font-bold">{{ item.label }}</span>
      </ButtonIcon>
    </template>
  </Breadcrumb>
  <Button text label="Expand all" icon="pi pi-plus" @click="expandAll" />
  <Button text label="Collapse all" icon="pi pi-minus" @click="collapseAll" />

  <BlockUI :blocked="loading">
    <HeaderRow
      class="grid grid-cols-[4%_4%_46%_15%_15%_20%] gap-y-2 items-center h-[50px] relative"
      :config="columnsConfig"
      v-model:filters="store.filters"
      v-model:ordering="store.ordering"
      @update:ordering="handleSort"
      v-model:checked-all="isAllChecked"
      @toggle:check-all="handleMarkAll"
      @update:filters="store.fetchData"
    />
    <Divider />
    <div class="h-[400px] relative" :class="listClass">
      <Preloader
        v-if="loading"
        class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-[0.8rem] leading-[1.3]"
      />

      <EmptyMessage
        v-else-if="!loading && !store.data.length"
        :message="emptyMessage"
      />
      <VirtualTree :nodes="rows" keyProp="path" :itemSize="50" appendOnly>
        <template #row="{ node }">
          <RowWrapper
            @move="handleMoveDrop"
            v-bind="node"
            :draggable="!store.uploadingData[node.path]"
            class="grid grid-cols-[4%_4%_10%_36%_15%_15%_20%] gap-y-2 items-center h-[50px] hover:bg-mask relative"
            :class="rowClass"
          >
            <template v-if="$slots.nodeExpand">
              <slot
                name="nodeExpand"
                :path="node.path"
                :children="node.children"
                v-bind="node"
              ></slot>
            </template>
            <NodeExpand v-else :path="node.path" :children="node.children" />

            <template v-if="$slots.checkbox">
              <slot
                name="checkbox"
                :path="node.path"
                :type="node.type"
                :is_dir="node.is_dir"
              ></slot>
            </template>
            <CheckboxCell v-else :path="node.path" />

            <template v-if="$slots.fileType">
              <slot
                name="fileType"
                :node="node"
                :path="node.path"
                :type="node.type"
                :duration="node.duration"
                @update:dir="handleUpdateDir"
                @trigger:image="openImage"
                @trigger:video="openSelectedVideo"
                :makeImagePreviewURL="
                  (path: string) => makeImagePreviewURL(path, store.mediaType)
                "
                :makeVideoPreviewURL="
                  (path: string) => makeVideoPreviewURL(path, store.mediaType)
                "
              />
            </template>
            <FileType
              v-else
              :path="node.path"
              :type="node.type"
              :duration="node.duration"
              @update:dir="handleUpdateDir"
              @trigger:image="openImage"
              @trigger:video="openSelectedVideo"
              @trigger:text="
                () => {
                  selectedTextFile = node;
                  selectedTextFile.url = makeDownloadURL(
                    store.mediaType,
                    node?.path,
                  );
                  textFilePopupVisible = true;
                }
              "
              :makeImagePreviewURL="
                (path: string) => makeImagePreviewURL(path, store.mediaType)
              "
              :makeVideoPreviewURL="
                (path: string) => makeVideoPreviewURL(path, store.mediaType)
              "
            />
            <template v-if="$slots.filename">
              <slot
                name="filename"
                @rename="handleRename"
                :path="node.path"
                :name="node.name"
                :progress="node.progress"
              ></slot>
            </template>
            <Filename
              v-else
              @rename="handleRename"
              :path="node.path"
              :name="node.name"
              :progress="node.progress"
            />
            <template v-if="$slots.size">
              <slot
                name="size"
                :children="node.children"
                :size="node.size"
                :type="node.type"
              ></slot>
            </template>
            <Size
              v-else
              :children="node.children"
              :size="node.size"
              :type="node.type"
            />
            <template v-if="$slots.modifiedTime">
              <slot name="modifiedTime" :modified="node.modified"></slot>
            </template>
            <ModifiedTime v-else :modified="node.modified" />
            <template v-if="$slots.actions">
              <slot
                name="actions"
                :path="node.path"
                :progress="node.progress"
                @download="handleDownloadFile"
                @remove="handleRemoveFile"
                @upload:cancel="handleCancelUpload"
              ></slot>
            </template>
            <Actions
              v-else
              :path="node.path"
              :progress="node.progress"
              @download="handleDownloadFile"
              @remove="handleRemoveFile"
              @upload:cancel="handleCancelUpload"
            />
            <div class="absolute bottom-0 left-0 w-full" v-if="node.progress">
              <ProgressBar
                :show-value="false"
                :value="node.progress"
              ></ProgressBar>
            </div>
          </RowWrapper>
        </template>
      </VirtualTree>
    </div>
  </BlockUI>
  <VideoGallery
    v-model:visible="videoPopupVisible"
    v-model:selected-item="selectedVideo"
    :items="videos"
    :makeVideoPreviewURL="
      (path: string) => makeVideoPreviewURL(path, store.mediaType)
    "
    :makeVideoURL="(path) => makeVideoURL(path, store.mediaType)"
    @after-hide="
      () => {
        popupStore.isEscapable =
          !galleryPopupVisible && !newDirectoryPopupVisible && !isDirChooseOpen;
      }
    "
  />
  <DirectoryChooser
    :scope="props.store.mediaType"
    v-model:visible="isDirChooseOpen"
    :header="movePopupHeader"
    @dir:submit="handleMoveMarked"
    @after-hide="
      () => {
        popupStore.isEscapable =
          !videoPopupVisible &&
          !newDirectoryPopupVisible &&
          !galleryPopupVisible;
      }
    "
  />

  <GalleryPopup
    v-model:selected-image-idx="selectedImageIdx"
    v-model:gallery-popup-visible="galleryPopupVisible"
    :images="images"
    titleProp="name"
    altProp="name"
    :getItemURL="(item) => makeImagePreviewURL(item.path, store.mediaType)"
    @after-hide="
      () => {
        popupStore.isEscapable =
          !videoPopupVisible && !newDirectoryPopupVisible && !isDirChooseOpen;
      }
    "
  />
  <MakeDirectoryPopup
    v-model:visible="newDirectoryPopupVisible"
    :currentDirectory="store.dir || store.root_dir"
    @after-hide="
      () => {
        popupStore.isEscapable =
          !galleryPopupVisible && !videoPopupVisible && !isDirChooseOpen;
      }
    "
  />
  <TextPopup
    :header="!selectedTextFile?.path ? 'New file' : selectedTextFile?.path"
    :dir="store.dir"
    :url="selectedTextFile?.url"
    :saveUrl="makeSaveURL(store.mediaType)"
    @submit:save="handleSubmitNewTextFile"
    v-model:visible="textFilePopupVisible"
    :path="selectedTextFile?.path"
  />
</template>

<script setup lang="ts">
import { provide, computed, onMounted, ref, useTemplateRef } from "vue";
import type { FileStore } from "@/features/files/store-fabric";
import type { GroupedFile } from "@/features/files/interface";
import InputText from "primevue/inputtext";
import HeaderRow from "@/features/files/components/HeaderRow.vue";
import { usePopupStore } from "@/features/settings/stores";
import {
  makeImagePreviewURL,
  makeVideoPreviewURL,
  makeVideoURL,
  makeDownloadURL,
  makeSaveURL,
} from "@/features/files/api";
import VirtualTree from "@/features/files/components/VirtualTree.vue";
import { isNumber, isEmpty } from "@/util/guards";

import {
  flattenExpandedTree,
  getExpandableIds,
  toBreadcrumbs,
  mergeRows,
} from "@/features/files/components/util";
import VideoGallery from "@/ui/VideoGallery.vue";

import { useAsyncDebounce } from "@/composables/useDebounce";
import { columnsConfig } from "@/features/files/components/config";
import ButtonIcon from "@/ui/ButtonIcon.vue";
import { omit } from "@/util/obj";
import DirectoryChooser from "@/features/files/components/DirectoryChooser.vue";
import RowWrapper from "@/features/files/components/RowWrapper.vue";
import CheckboxCell from "@/features/files/components/Cells/CheckboxCell.vue";
import Actions from "@/features/files/components/Cells/Actions.vue";
import ModifiedTime from "@/features/files/components/Cells/ModifiedTime.vue";
import Size from "@/features/files/components/Cells/Size.vue";
import Filename from "@/features/files/components/Cells/Filename.vue";
import FileType from "@/features/files/components/Cells/FileType.vue";
import NodeExpand from "@/features/files/components/Cells/NodeExpand.vue";

import { startCase } from "@/util/str";
import BatchActionsHeader from "@/features/files/components/BatchActionsHeader.vue";
import GalleryPopup from "@/features/files/components/GalleryPopup.vue";
import MakeDirectoryPopup from "@/features/files/components/MakeDirectoryPopup.vue";
import Uploader from "@/features/files/components/Uploader.vue";
import Preloader from "@/features/files/components/Preloader.vue";
import EmptyMessage from "@/features/files/components/EmptyMessage.vue";
import TextPopup from "@/features/files/components/TextPopup.vue";

const props = withDefaults(
  defineProps<{
    store: FileStore;
    uploadURL?: string;
    rowClass?: string;
    listClass?: string;
  }>(),
  {},
);

const uploaderRef = useTemplateRef("uploaderRef");

const videoPopupVisible = ref<boolean>(false);
const selectedVideo = ref<GroupedFile>();

const galleryPopupVisible = ref<boolean>(false);

const loading = computed(() => props.store.loading);
const expandedNodes = ref<Set<string>>(new Set());
const markedNodes = ref<Record<string, boolean>>({});
const emptyMessage = computed(() => props.store.emptyMessage);

const popupStore = usePopupStore();
const newDirectoryPopupVisible = ref<boolean>(false);

const selectedTextFile = ref<Partial<GroupedFile & { url: string }>>({});
const textFilePopupVisible = ref<boolean>(false);

const selectedImageIdx = ref<number>(0);
const expandedFlattenItems = computed(() =>
  flattenExpandedTree("path", props.store.data, expandedNodes.value),
);

const dirs = computed(() =>
  expandedFlattenItems.value.reduce(
    (acc, item) => {
      if (item.is_dir) {
        acc[item.path] = true;
      }

      return acc;
    },
    {} as Record<string, boolean>,
  ),
);

const markedFilenames = computed(() =>
  Object.keys(markedNodes.value).filter((key) => markedNodes.value[key]),
);

const loadingRows = computed(() => ({
  ...props.store.removingRows,
  ...props.store.downloadingRows,
}));

const rows = computed(() => {
  if (isEmpty(props.store.uploadingData)) {
    return props.store.data;
  }
  const currentDir = props.store.dir;
  if (currentDir) {
    return mergeRows(props.store.data, currentDir, props.store.uploadingData);
  }

  return mergeRows(props.store.data, "", props.store.uploadingData);
});

const isAllChecked = ref<boolean>(false);
const isDirChooseOpen = ref<boolean>(false);

const breadcrumbHome = computed(() => ({
  label: props.store.root_dir,
}));

const markedLen = computed(() => markedFilenames.value.length);

const breadcrumbItems = computed(() =>
  props.store.dir ? toBreadcrumbs(props.store.dir) : [],
);

const movePopupHeader = computed(() =>
  markedLen.value === 1
    ? `Move ${markedFilenames.value[0]} to:`
    : `Move ${markedLen.value} files to:`,
);

const handleSubmitNewTextFile = ({ path }: { path: string }) => {
  selectedTextFile.value.path = path;
  props.store.fetchData();
};

const handleCancelUpload = (filepath: string) => {
  uploaderRef.value?.handleCancelUpload(filepath);
};

const handleMoveMarked = async (targetDir: string) => {
  const filenames = markedFilenames.value;
  await props.store.batchMoveFiles(filenames, targetDir);
  markedNodes.value = omit(filenames, markedNodes.value);
};

const handleMoveDrop = async (targetDir: string, filePaths: string[]) => {
  if (filePaths.length > 1) {
    await props.store.batchMoveFiles(filePaths, targetDir);
  } else {
    await props.store.batchMoveFiles(filePaths, targetDir);
  }
  markedNodes.value = omit(filePaths, markedNodes.value);
};

const openCreateDirectoryPopup = async () => {
  newDirectoryPopupVisible.value = true;
};

const handleDownloadFile = (name: string) => {
  props.store.downloadFile(name);
};

const handleRemoveFile = async (name: string) => {
  await props.store.removeFile(name);
};

const expandAll = () => {
  expandedNodes.value = getExpandableIds("path", props.store.data);
};

const collapseAll = () => {
  expandedNodes.value = new Set<string>();
};

const markAll = () => {
  expandedFlattenItems.value.forEach((item) => {
    markedNodes.value[item.path] = true;
  });
};

const unmarkAll = () => {
  expandedFlattenItems.value.forEach((item) => {
    delete markedNodes.value[item.path];
  });
};

const handleUpdateDir = (path: string) => {
  props.store.dir = path;
  props.store.data = [];
  props.store.fetchData();
};

const handleRename = (path: string, newName: string) => {
  props.store.renameFile(path, newName);
};

const groupedItems = computed(() =>
  expandedFlattenItems.value.reduce(
    (acc, node) => {
      if (!acc[node.type]) {
        acc[node.type] = [];
      }
      acc[node.type].push(node);
      return acc;
    },
    {} as Record<string, GroupedFile[]>,
  ),
);

const images = computed(() => groupedItems.value["image"] || []);
const videos = computed(() => groupedItems.value["video"] || []);

const openImage = (itemPath: string) => {
  selectedImageIdx.value = images.value.findIndex(
    ({ path }) => itemPath === path,
  );
  if (isNumber(selectedImageIdx.value)) {
    popupStore.isEscapable = false;
    galleryPopupVisible.value = true;
  }
};

const openSelectedVideo = (itemPath: string) => {
  selectedVideo.value = videos.value.find(({ path }) => itemPath === path);

  if (selectedVideo.value) {
    popupStore.isEscapable = false;
    videoPopupVisible.value = true;
  }
};

const handleSearch = useAsyncDebounce(async (value: string | undefined) => {
  await props.store.fetchData();
  if (value && value.length > 0) {
    expandAll();
  }
}, 500);

const handleSort = () => {
  props.store.fetchData();
};

const handleMarkAll = (value: boolean) => {
  if (value) {
    markAll();
  } else {
    unmarkAll();
  }
};

provide("expandedNodes", expandedNodes);
provide("markedNodes", markedNodes);
provide("markedFilenames", markedFilenames);
onMounted(props.store.fetchData);
</script>
