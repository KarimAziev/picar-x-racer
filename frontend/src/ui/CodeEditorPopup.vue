<template>
  <Dialog
    :content-class="contentClass"
    :header="path"
    v-model:visible="visible"
    :closeOnEscape="false"
    closable
    @show="openPopup"
    @hide="afterHide"
    @maximize="
      () => {
        isMaximized = true;
      }
    "
    @unmaximize="
      () => {
        isMaximized = false;
      }
    "
    @after-hide="afterHide"
    v-bind="
      omit(
        ['url', 'path', 'saveUrl', 'normalizePayload', 'responseContentProp'],
        props,
      )
    "
  >
    <template #header>
      <div v-if="!path" class="flex flex-col">
        <div class="font-bold">Filename:</div>
        <InputText
          autocomplete="off"
          inputId="new-text-file"
          class="!w-50"
          id="new-text-file"
          :pt="{ pcInput: { id: 'new-text-file' } }"
          @update:model-value="handleValidateFilename"
          v-model="filePathName"
          :invalid="!!invalidMessages.filename"
        />
        <div class="bg-transparent text-red-500 text-sm">
          {{ invalidMessages.filename }}&nbsp;
        </div>
      </div>
      <div v-else>{{ path }}</div>
      <div class="flex-auto flex justify-end">
        <SelectField
          class="w-40"
          label="Language"
          :options="languagesOptions"
          v-model="selectedLanguage"
          @update:model-value="
            () => {
              isLangManuallyChoosen = true;
            }
          "
        />
      </div>
    </template>
    <Preloader v-if="loading" />
    <EmptyMessage v-else-if="emptyMessage" :message="emptyMessage" />
    <div style="position: relative">
      <CodeMirror
        @search:open="handleSearchOpen"
        @search:close="handleSearchClose"
        :class="heightClass"
        v-model:model-value="content"
        @update:model-value="handleValidateText"
        :language="
          selectedLanguage
            ? getCodemirrorLang(selectedLanguage)
            : guessedLanguage
        "
      />
    </div>
    <Skeleton v-if="loading" :class="heightClass"></Skeleton>
    <div v-if="isNumber(progress)">
      <ProgressBar :show-value="false" :value="progress"></ProgressBar>
    </div>

    <template #footer>
      <div class="flex gap-x-2 mt-2">
        <span class="flex justify-start gap-x-4">
          <Button
            type="button"
            label="Save"
            v-if="props.saveUrl"
            :disabled="isDisabled"
            @click="handleSave"
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
import { ref, computed, watch, nextTick } from "vue";
import axios from "axios";
import type { DialogProps } from "primevue/dialog";
import { usePopupStore } from "@/features/settings/stores";
import { retrieveError } from "@/util/error";
import Preloader from "@/features/files/components/Preloader.vue";
import EmptyMessage from "@/features/files/components/EmptyMessage.vue";
import { isNumber, isEmptyString } from "@/util/guards";
import type { Nullable } from "@/util/ts-helpers";
import SelectField from "@/ui/SelectField.vue";

import {
  findLang,
  getLanguageOptions,
  mapLanguagesHash,
} from "@/util/codemirror";
import CodeMirror from "@/ui/CodeMirror.vue";
import { omit } from "@/util/obj";
import { useKeyboardHandlers } from "@/composables/useKeyboardHandlers";

const popupStore = usePopupStore();

const emit = defineEmits(["after-hide", "submit:save"]);
const loading = ref(false);
const saving = ref(false);
const emptyMessage = ref<Nullable<string>>(null);

type NormalizePayload = (content: string, filename: string) => any;

export interface Props
  extends Omit<
    DialogProps,
    "visible" | "header" | "contentClass" | "closeOnEscape" | "closable"
  > {
  path?: string;
  url?: string;
  saveUrl?: string;
  normalizePayload: NormalizePayload;
  responseContentProp?: string;
}

const props = withDefaults(defineProps<Props>(), {
  responseContentProp: "content",
  maximizable: true,
  modal: true,
  dismissableMask: true,
  autoZIndex: true,
  showHeader: true,
  draggable: true,
});

const closeOnEscape = ref(true);

const handleSearchOpen = () => {
  closeOnEscape.value = false;
};

const handleSearchClose = async () => {
  await nextTick();
  closeOnEscape.value = true;
};

const maybeClose = () => {
  if (closeOnEscape.value) {
    handleCancel();
  }
};
const { addKeyEventListeners, removeKeyEventListeners } = useKeyboardHandlers({
  Escape: maybeClose,
});

const visible = defineModel<boolean>("visible", {
  required: true,
});

const invalidMessages = ref<{
  filename: Nullable<string>;
  text: Nullable<string>;
}>({ filename: null, text: null });

const isLangManuallyChoosen = ref(false);

const languagesOptions = computed(() => getLanguageOptions());
const heightClass = computed(() =>
  isMaximized.value ? "min-h-[90vh]" : "min-h-[55vh]",
);

const contentClass = computed(() =>
  isMaximized.value
    ? "w-[100vw] h-[100vh] p-10"
    : "w-[95vw] sm:w-[600px] md:w-[700px] lg:w-[1000px] xl:w-[1200px] min-h-[55vh] p-10",
);

const progress = ref<Nullable<number>>(null);

const isMaximized = ref(false);
const content = ref<Nullable<string>>(null);
const origContent = ref<Nullable<string>>(null);

const filePathName = ref<Nullable<string>>(null);
const languagesHash = computed(() => mapLanguagesHash());

const guessedLanguage = computed(() => {
  const filePath = props.path || filePathName.value;
  if (!filePath) {
    return;
  }
  return findLang(filePath);
});

const selectedLanguage = ref(guessedLanguage.value?.name);
const isDisabled = computed(
  () =>
    !!invalidMessages.value.filename ||
    !!invalidMessages.value.text ||
    saving.value ||
    loading.value ||
    origContent.value === content.value,
);

const getCodemirrorLang = (name?: string) =>
  name ? languagesHash.value.get(name) : undefined;

const handleValidateText = (newValue?: Nullable<string>) => {
  if (newValue && !isEmptyString(newValue.trim())) {
    invalidMessages.value.text = null;
  } else {
    invalidMessages.value.text = "Required";
  }
};

const handleValidateFilename = (newValue?: Nullable<string>) => {
  if (props.path) {
    invalidMessages.value.filename = null;
    return;
  }
  if (newValue && !isEmptyString(newValue.trim())) {
    invalidMessages.value.filename = null;
  } else {
    invalidMessages.value.filename = "Required";
  }
};

const openPopup = async () => {
  popupStore.isEscapable = false;
  addKeyEventListeners();
  try {
    if (!props.url) {
      return;
    }
    loading.value = true;
    emptyMessage.value = null;
    progress.value = 0;
    const response = await axios.get<string>(props.url, {
      responseType: "text",
      onDownloadProgress: (progressEvent) => {
        if (isNumber(progressEvent.total)) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total,
          );
          progress.value = percentCompleted;
        }
      },
    });
    origContent.value = response.data;
    content.value = response.data;
  } catch (error) {
    const errData = retrieveError(error);
    emptyMessage.value = errData.text.length > 0 ? errData.text : errData.title;
  } finally {
    progress.value = null;
    loading.value = false;
  }
};

const handleSave = async () => {
  const filename = props.path || filePathName.value;

  if (!props.saveUrl || !content.value || !filename) {
    return;
  }
  try {
    emptyMessage.value = null;
    saving.value = true;
    const payload = props.normalizePayload(content.value, filename);

    const response = await axios.put(props.saveUrl, payload);
    const savedContent =
      props.responseContentProp && response.data[props.responseContentProp];

    if (savedContent) {
      origContent.value = savedContent;
      emit("submit:save", response.data);
    }
  } catch (error) {
    const errData = retrieveError(error);
    emptyMessage.value = errData.text.length > 0 ? errData.text : errData.title;
  } finally {
    saving.value = false;
  }
};

const handleCancel = () => {
  visible.value = false;
  afterHide();
};

const afterHide = () => {
  removeKeyEventListeners();
  closeOnEscape.value = true;
  invalidMessages.value.text = null;
  invalidMessages.value.filename = null;
  filePathName.value = null;
  selectedLanguage.value = undefined;
  content.value = null;
  isLangManuallyChoosen.value = false;
  origContent.value = null;
  emptyMessage.value = null;
  popupStore.isEscapable = true;
  progress.value = null;
  emit("after-hide");
};

watch(
  () => guessedLanguage.value,
  (lang) => {
    if (lang && !isLangManuallyChoosen.value) {
      selectedLanguage.value = lang.name;
    }
  },
);
</script>
