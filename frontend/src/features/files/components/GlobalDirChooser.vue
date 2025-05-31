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
        class="grid grid-cols-[4%_4%_62%_15%_15%] gap-y-2 items-center h-[50px] relative"
        :config="directoryChooserColumnsConfig"
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
              class="grid grid-cols-[4%_10%_52%_15%_15%] gap-y-2 items-center h-[40px] hover:bg-mask relative"
            >
              <Cell>
                <RadioButton
                  v-if="isDirectoryType(node.type)"
                  v-model="selectedItem"
                  :inputId="`${node.path}-dir-choose`"
                  :value="node.path"
                />
              </Cell>
              <FileType
                :path="node.path"
                :type="node.type"
                :duration="node.duration"
                @update:dir="handleUpdateDir"
              />
              <Filename disabled :path="node.path" :name="node.name" />
              <Size
                :children_count="node.children_count"
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
            :disabled="submitDisabled"
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
import type {
  GroupedFile,
  FileResponseModel,
  FileFilterRequest,
  OrderingModel,
} from "@/features/files/interface";
import VirtualTree from "@/features/files/components/VirtualTree.vue";
import Cell from "@/features/files/components/Cell.vue";
import {
  toBreadcrumbs,
  isDirectoryType,
} from "@/features/files/components/util";
import { useAsyncDebounce } from "@/composables/useDebounce";
import ButtonIcon from "@/ui/ButtonIcon.vue";
import { FilterMatchMode, SortDirection } from "@/features/files/enums";
import { Nullable } from "@/util/ts-helpers";
import { useMessagerStore } from "@/features/messager";
import { directoryChooserColumnsConfig } from "@/features/files/components/config";
import HeaderRow from "@/features/files/components/HeaderRow.vue";

import RowWrapper from "@/features/files/components/RowWrapper.vue";
import Filename from "@/features/files/components/Cells/Filename.vue";
import Size from "@/features/files/components/Cells/Size.vue";
import FileType from "@/features/files/components/Cells/FileType.vue";
import ModifiedTime from "@/features/files/components/Cells/ModifiedTime.vue";
import { appApi } from "@/api";

const props = withDefaults(
  defineProps<{
    itemSize?: number;
    scope?: Nullable<string>;
    header?: string;
    dir?: Nullable<string>;
  }>(),
  {
    itemSize: 50,
  },
);

const visible = defineModel<boolean>("visible", { required: true });
const emit = defineEmits(["show", "after-hide", "dir:submit"]);
const selectedItem = ref<Nullable<string>>(null);
const initialDir = ref<Nullable<string>>(null);

const submitDisabled = computed(
  () => !selectedItem.value && initialDir.value === currentDir.value,
);

const handleShow = () => {
  initialDir.value = props.dir;
  currentDir.value = props.dir;
  fetchData();
  emit("show");
};
const handleHide = () => {
  initialDir.value = null;
  selectedItem.value = null;
  currentDir.value = null;
  emit("after-hide");
};

const handleSubmit = () => {
  visible.value = false;
  if (!selectedItem.value) {
    selectedItem.value = currentDir.value;
  }

  if (selectedItem.value) {
    emit("dir:submit", selectedItem.value);
    selectedItem.value = null;
  }
};

const handleCancel = () => {
  selectedItem.value = undefined;
  visible.value = false;
};

const currentDir = ref<Nullable<string>>(props.dir);

const rows = ref<GroupedFile[]>([]);
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
  label: "/",
  value: "/",
}));

const breadcrumbItems = computed(() => toBreadcrumbs(currentDir.value || "/"));

const expandedNodes = ref<Set<string>>(new Set());

const emptyMessage = ref("No data");

const handleSearch = useAsyncDebounce(async () => {
  await fetchData();
}, 500);

const handleSort = () => {
  fetchData();
};

async function fetchData() {
  const messager = useMessagerStore();
  try {
    loading.value = true;
    const response = await appApi.post<FileResponseModel>("/api/files/list", {
      root_dir: currentDir.value,
      search: search.value,
      filters: {
        type: {
          match_mode: FilterMatchMode.IN,
          value: [],
        },
      },
      ordering: ordering.value,
    });

    rows.value = response.data;
    currentDir.value = response.root_dir;
  } catch (error) {
    messager.handleError(error, "Error fetching data");
    emptyMessage.value = "Failed to fetch data";
  } finally {
    loading.value = false;
  }
}

const handleUpdateDir = (filepath: string) => {
  selectedItem.value = null;
  currentDir.value = filepath;
  search.value.value = "";
  fetchData();
};

provide("expandedNodes", expandedNodes);
</script>
