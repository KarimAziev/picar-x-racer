<template>
  <Fieldset
    legend="Filters"
    toggleable
    collapsed
    class="min-w-[350px] sm:w-[630px]"
  >
    <div class="flex flex-col gap-y-2">
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
              :inputId="`filter-id-${field}-${store.mediaType}`"
              :options="options"
              class="w-40"
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
        <div class="flex gap-2 items-center">
          <DatePickerField
            showButtonBar
            :inputId="`from-date-${store.mediaType}`"
            class="w-40"
            @update:model-value="store.fetchData"
            v-model:model-value="store.filters.modified.constraints[0].value"
            label="From Date"
          />
          <DatePickerField
            showButtonBar
            :inputId="`to-date-${store.mediaType}`"
            class="w-40"
            @update:model-value="store.fetchData"
            v-model:model-value="store.filters.modified.constraints[1].value"
            label="To Date"
          />
        </div>
      </div>
      <div class="flex gap-2">
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
      outlined
      severity="secondary"
      @click="openCreateDirectoryPopup"
      label="New directory"
      icon="pi pi-folder-plus"
    ></Button>
    <Button
      outlined
      severity="secondary"
      @click="
        () => {
          textFilePopupVisible = true;
        }
      "
      label="New  file"
      icon="pi pi-file-plus"
    ></Button>
    <Button
      severity="secondary"
      outlined
      @click="
        () => {
          store.fetchData(currentDir);
        }
      "
      label="Refresh"
      icon="pi pi-refresh"
    ></Button>

    <Uploader
      class="!rounded-s-none"
      :currentDir="currentDir"
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

  <Breadcrumb :model="breadcrumbItems" :home="breadcrumbHome">
    <template #item="{ item }">
      <ButtonIcon
        :icon="item.icon"
        text
        class="font-bold"
        @click="handleUpdateDir(item.value)"
      >
        <span class="font-bold">{{ item.label }}</span>
      </ButtonIcon>
    </template>
  </Breadcrumb>
  <div class="flex gap-2 items-center">
    <template v-if="$slots.headerButtons">
      <slot name="headerButtons" />
    </template>
  </div>

  <BlockUI :blocked="loading">
    <HeaderRow
      class="grid grid-cols-[2%_6%_40%_15%_20%_17%] gap-y-2 items-center h-[50px] relative"
      :config="columnsConfig"
      v-model:filters="store.filters"
      v-model:ordering="store.ordering"
      @update:ordering="handleSort"
      v-model:checked-all="isAllChecked"
      @toggle:check-all="handleMarkAll"
      @update:filters="store.fetchData"
    />
    <Divider />
    <div class="h-[300px] sm:h-[400px] relative" :class="listClass">
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
            class="grid grid-cols-[4%_10%_32%_20%_15%_20%] gap-y-2 items-center h-[50px] hover:bg-mask relative"
            :class="rowClass"
          >
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
                    node?.path,
                    store.mediaType,
                  );
                  textFilePopupVisible = true;
                }
              "
              :makeAudioURL="
                (path: string) => makeAudioURL(path, store.mediaType)
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
                :size="node.size"
                :type="node.type"
                :children_count="node.children_count"
              ></slot>
            </template>
            <Size
              v-else
              :children_count="node.children_count"
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
  <GlobalDirChooser
    :scope="store.mediaType"
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
    :currentDirectory="store.root_dir || store.dir"
    @submit:dir="store.makeDir"
    @after-hide="
      () => {
        popupStore.isEscapable =
          !galleryPopupVisible && !videoPopupVisible && !isDirChooseOpen;
      }
    "
  />
  <CodeEditorPopup
    :url="selectedTextFile?.url"
    :header="!selectedTextFile?.path ? 'New file' : selectedTextFile?.path"
    :saveUrl="makeSaveURL(store.mediaType)"
    @submit:save="handleSubmitNewTextFile"
    v-model:visible="textFilePopupVisible"
    :normalizePayload="
      (content, filename) => ({
        path: filename,
        content: content,
        dir: store.root_dir,
      })
    "
    @after-hide="
      () => {
        selectedTextFile = {};
      }
    "
    :path="selectedTextFile?.path"
  />
</template>

<script setup lang="ts">
import {
  provide,
  computed,
  onMounted,
  ref,
  useTemplateRef,
  defineAsyncComponent,
} from "vue";
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
  makeAudioURL,
  makeUploadURL,
} from "@/features/files/api";
import VirtualTree from "@/features/files/components/VirtualTree.vue";
import { isNumber, isEmpty } from "@/util/guards";

import {
  flattenExpandedTree,
  toBreadcrumbs,
  mergeRows,
} from "@/features/files/components/util";

import { useAsyncDebounce } from "@/composables/useDebounce";
import { columnsConfig } from "@/features/files/components/config";
import ButtonIcon from "@/ui/ButtonIcon.vue";
import { omit } from "@/util/obj";
import RowWrapper from "@/features/files/components/RowWrapper.vue";
import CheckboxCell from "@/features/files/components/Cells/CheckboxCell.vue";
import Actions from "@/features/files/components/Cells/Actions.vue";
import ModifiedTime from "@/features/files/components/Cells/ModifiedTime.vue";
import Size from "@/features/files/components/Cells/Size.vue";
import Filename from "@/features/files/components/Cells/Filename.vue";
import FileType from "@/features/files/components/Cells/FileType.vue";

import { startCase } from "@/util/str";
import BatchActionsHeader from "@/features/files/components/BatchActionsHeader.vue";
import Uploader from "@/features/files/components/Uploader.vue";
import Preloader from "@/features/files/components/Preloader.vue";
import EmptyMessage from "@/features/files/components/EmptyMessage.vue";
import DatePickerField from "@/ui/DatePickerField.vue";
import { useFileExplorer } from "@/features/files/stores";
import CodeEditorPopup from "@/ui/CodeEditorPopup.vue";
import { expandFileName } from "@/features/files/util";

withDefaults(
  defineProps<{
    rowClass?: string;
    listClass?: string;
  }>(),
  {},
);

const GalleryPopup = defineAsyncComponent({
  loader: () => import("@/features/files/components/GalleryPopup.vue"),
});

const MakeDirectoryPopup = defineAsyncComponent({
  loader: () => import("@/features/files/components/MakeDirectoryPopup.vue"),
});

const GlobalDirChooser = defineAsyncComponent({
  loader: () => import("@/features/files/components/GlobalDirChooser.vue"),
});
const VideoGallery = defineAsyncComponent({
  loader: () => import("@/ui/VideoGallery.vue"),
});
const store = useFileExplorer();
const uploadURL = computed(() => makeUploadURL(null));

const uploaderRef = useTemplateRef("uploaderRef");

const videoPopupVisible = ref<boolean>(false);
const selectedVideo = ref<GroupedFile>();

const galleryPopupVisible = ref<boolean>(false);

const loading = computed(() => store.loading);
const expandedNodes = ref<Set<string>>(new Set());
const markedNodes = ref<Record<string, boolean>>({});
const emptyMessage = computed(() => store.emptyMessage);

const popupStore = usePopupStore();
const newDirectoryPopupVisible = ref<boolean>(false);

const selectedTextFile = ref<Partial<GroupedFile & { url: string }>>({});
const textFilePopupVisible = ref<boolean>(false);

const currentDir = computed(() => store.root_dir);

const selectedImageIdx = ref<number>(0);
const expandedFlattenItems = computed(() =>
  flattenExpandedTree("path", store.data, expandedNodes.value),
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
  ...store.removingRows,
  ...store.downloadingRows,
}));

const rows = computed(() => {
  if (isEmpty(store.uploadingData)) {
    return store.data;
  }
  const currentDir = store.root_dir;
  if (currentDir) {
    return mergeRows(store.data, currentDir, store.uploadingData);
  }

  return mergeRows(store.data, "", store.uploadingData);
});

const isAllChecked = ref<boolean>(false);
const isDirChooseOpen = ref<boolean>(false);

const breadcrumbItems = computed(() => toBreadcrumbs(store.root_dir || "/"));

const breadcrumbHome = computed(() => ({
  label: "/",
  value: "/",
}));

const markedLen = computed(() => markedFilenames.value.length);

const movePopupHeader = computed(() =>
  markedLen.value === 1
    ? `Move ${markedFilenames.value[0]} to:`
    : `Move ${markedLen.value} files to:`,
);

const handleSubmitNewTextFile = ({ path }: { path: string }) => {
  selectedTextFile.value.path = path;
  store.fetchData();
};

const handleCancelUpload = (filepath: string) => {
  uploaderRef.value?.handleCancelUpload(filepath);
};

const handleMoveMarked = async (targetDir: string) => {
  const filenames = markedFilenames.value;
  await store.batchMoveFiles(filenames, targetDir);
  markedNodes.value = omit(filenames, markedNodes.value);
};

const handleMoveDrop = async (targetDir: string, filePaths: string[]) => {
  if (filePaths.length > 1) {
    await store.batchMoveFiles(filePaths, targetDir);
  } else {
    await store.batchMoveFiles(filePaths, targetDir);
  }
  markedNodes.value = omit(filePaths, markedNodes.value);
};

const openCreateDirectoryPopup = async () => {
  newDirectoryPopupVisible.value = true;
};

const handleDownloadFile = (name: string) => {
  store.downloadFile(name);
};

const handleRemoveFile = async (name: string) => {
  await store.removeFile(name);
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

const handleUpdateDir = async (path: string) => {
  store.data = [];
  store.search.value = "";
  await store.fetchData(path);
};

const handleRename = (path: string, newName: string) => {
  store.renameFile(path, expandFileName(newName, currentDir.value));
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

const handleSearch = useAsyncDebounce(async () => {
  await store.fetchData();
}, 500);

const handleSort = () => {
  store.fetchData();
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

onMounted(store.fetchData);
</script>
