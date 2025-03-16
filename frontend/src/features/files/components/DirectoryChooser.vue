<template>
  <Dialog
    :header="header"
    content-class="min-w-[350px] sm:min-w-[500px] md:min-w-[600px]"
    v-model:visible="visible"
    dismissableMask
    modal
    @show="handleShow"
    @after-hide="handleHide"
  >
    <div class="flex items-center">
      <Button text label="Expand all" icon="pi pi-plus" @click="expandAll" />
      <Button
        text
        label="Collapse all"
        icon="pi pi-minus"
        @click="collapseAll"
      />
      <div class="flex flex-auto justify-end">
        <div class="search-field">
          <InputText
            @update:model-value="handleSearch"
            class="max-w-20"
            id="search-models"
            v-model="search.value"
            :pt="{ pcInput: { id: 'search-files' } }"
            placeholder="Search"
          />
        </div>
      </div>
    </div>
    <div class="flex">
      <Breadcrumb :home="breadcrumbHome" :model="breadcrumbItems">
        <template #item="{ item }">
          <ButtonIcon
            :disabled="currentDir === item.value"
            :icon="item.icon"
            text
            @click="handleUpdateDir(item.value)"
          >
            {{ item.label }}
          </ButtonIcon>
        </template>
      </Breadcrumb>
    </div>
    <BlockUI :blocked="loading">
      <HeaderRow
        :config="columnsConfig"
        v-model:ordering="ordering"
        :selectable="false"
        @update:ordering="handleSort"
      />
      <div class="h-[500px] relative">
        <div
          v-if="loading"
          class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-[0.8rem] leading-[1.3]"
        >
          <ProgressSpinner />
        </div>
        <div v-else-if="!loading && !rows.length" class="text-center">
          {{ emptyMessage }}
        </div>
        <VirtualTree
          rowClass="h-[50px] hover:bg-mask"
          :nodes="rows"
          keyProp="path"
          :itemSize="itemSize"
        >
          <template #row="{ node }">
            <RowWrapper
              v-bind="node"
              :draggable="false"
              class="grid grid-cols-[3%_5%_10%_50%_15%_15%] gap-y-2 items-center h-[50px] hover:bg-mask relative"
            >
              <div>
                <RadioButton
                  v-if="isDirectoryType(node.type)"
                  v-model="selectedItem"
                  :inputId="`${node.path}-dir-choose`"
                  :value="node.path"
                />
              </div>
              <NodeExpand :path="node.path" :children="node.children" />
              <FileType
                :path="node.path"
                :type="node.type"
                :duration="node.duration"
                @update:dir="handleUpdateDir"
              />
              <Filename disabled :path="node.path" :name="node.name" />
              <Size
                :children="node.children"
                :size="node.size"
                :type="node.type"
              />
              <ModifiedTime :modified="node.modified" />
            </RowWrapper>
          </template>
        </VirtualTree>
      </div>
    </BlockUI>
    <template #footer>
      <div class="flex gap-x-2 mt-2">
        <span class="flex justify-start gap-x-4">
          <Button
            type="button"
            label="Move"
            :disabled="!selectedItem"
            @click="handleSubmit"
          ></Button>
          <Button
            type="button"
            outlined
            label="Close"
            @click="handleCancel"
          ></Button>
        </span>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, provide } from "vue";
import axios from "axios";
import type {
  GroupedFile,
  FileResponseModel,
  FileFilterRequest,
  OrderingModel,
} from "@/features/files/interface";
import VirtualTree from "@/features/files/components/VirtualTree.vue";
import {
  getExpandableIds,
  toBreadcrumbs,
  isDirectoryType,
} from "@/features/files/components/util";
import { useAsyncDebounce } from "@/composables/useDebounce";
import ButtonIcon from "@/ui/ButtonIcon.vue";
import { FilterMatchMode, SortDirection } from "@/features/files/enums";
import { Nullable } from "@/util/ts-helpers";
import { useMessagerStore } from "@/features/messager";
import type { FileDetail } from "@/features/files/interface";

import type { TableColumnsConfig } from "@/features/files/components/config";
import HeaderRow from "@/features/files/components/HeaderRow.vue";

import RowWrapper from "@/features/files/components/RowWrapper.vue";
import Filename from "@/features/files/components/Cells/Filename.vue";
import Size from "@/features/files/components/Cells/Size.vue";
import NodeExpand from "@/features/files/components/Cells/NodeExpand.vue";
import FileType from "@/features/files/components/Cells/FileType.vue";
import ModifiedTime from "@/features/files/components/Cells/ModifiedTime.vue";

const props = withDefaults(
  defineProps<{
    itemSize?: number;
    scope: string;
    header?: string;
  }>(),
  {
    itemSize: 40,
  },
);

const columnsConfig: TableColumnsConfig<FileDetail> = {
  name: {
    class: "block w-[50%] truncate",
    title: "Name",
    sortable: true,
  },
  size: {
    title: "Size",
    sortable: true,
    class: "flex-auto justify-self-end justify-end",
  },
};
const visible = defineModel<boolean>("visible", { required: true });
const emit = defineEmits(["show", "after-hide", "dir:submit"]);
const selectedItem = ref<string>();

const handleShow = () => {
  fetchData();
  emit("show");
};
const handleHide = () => {
  emit("after-hide");
};

const handleSubmit = () => {
  visible.value = false;

  if (selectedItem.value) {
    emit("dir:submit", selectedItem.value);
    selectedItem.value = undefined;
  }
};

const handleCancel = () => {
  selectedItem.value = undefined;
  visible.value = false;
};

const currentDir = ref<Nullable<string>>();

const rows = ref<GroupedFile[]>([]);
const rootDir = ref<string>();
const search = ref<FileFilterRequest["search"]>({
  value: "",
  field: "name",
});
const loading = ref(false);

const ordering = ref<OrderingModel>({
  field: "modified",
  direction: SortDirection.DESC,
});

const breadcrumbHome = computed(() => ({
  label: rootDir.value,
}));

const breadcrumbItems = computed(() =>
  currentDir.value ? toBreadcrumbs(currentDir.value) : [],
);

const expandedNodes = ref<Set<string>>(new Set());

const emptyMessage = ref("No data");

const expandAll = () => {
  expandedNodes.value = getExpandableIds("path", rows.value);
};

const collapseAll = () => {
  expandedNodes.value = new Set<string>();
};

const handleSearch = useAsyncDebounce(async (value: string | undefined) => {
  await fetchData();
  if (value && value.length > 0) {
    expandAll();
  }
}, 500);

const handleSort = () => {
  fetchData();
};

async function fetchData() {
  const messager = useMessagerStore();
  try {
    loading.value = true;
    const response = await axios.post<FileResponseModel>(
      `/api/files/list/${props.scope}`,
      {
        dir: currentDir.value,
        search: search.value,
        filters: {
          type: {
            match_mode: FilterMatchMode.IN,
            value: [],
          },
        },
        ordering: ordering.value,
      },
    );

    rows.value = response.data.data;
    currentDir.value = response.data.dir;
    rootDir.value = response.data.root_dir;
  } catch (error) {
    messager.handleError(error, "Error fetching data");
    emptyMessage.value = "Failed to fetch data";
  } finally {
    loading.value = false;
  }
}

const handleUpdateDir = (filepath: string) => {
  currentDir.value = filepath;
  fetchData();
};

provide("expandedNodes", expandedNodes);
</script>

<style scoped lang="scss"></style>
