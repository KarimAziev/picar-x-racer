<template>
  <Dialog
    :content-class="
      isMaximized
        ? 'w-full h-full p-10'
        : 'sm:w-[600px] md:w-[700px] lg:w-[1000px] xl:w-[1200px] min-h-[55vh] p-10'
    "
    :header="header || path"
    v-model:visible="visible"
    dismissableMask
    @show="openPopup"
    maximizable
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
    modal
    @after-hide="afterHide"
  >
    <div v-if="!path" class="flex flex-col">
      <div class="font-bold">Filename:</div>
      <InputText
        inputId="new-text-file"
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
    <Preloader v-if="loading" />
    <EmptyMessage v-else-if="emptyMessage" :message="emptyMessage" />
    <Textarea
      :class="heightClass"
      :invalid="!!invalidMessages.text"
      v-else
      fluid
      :name="path"
      v-model="content"
      ref="textAreaRef"
      @update:model-value="handleValidateText"
      autoResize
    />
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
import { nextTick, ref, ComponentPublicInstance, computed } from "vue";
import axios from "axios";

import { usePopupStore } from "@/features/settings/stores";
import { retrieveError } from "@/util/error";
import Preloader from "@/features/files/components/Preloader.vue";
import EmptyMessage from "@/features/files/components/EmptyMessage.vue";
import { isNumber, isEmptyString } from "@/util/guards";
import type { Nullable } from "@/util/ts-helpers";

const popupStore = usePopupStore();

const emit = defineEmits(["after-hide", "submit:save"]);
const loading = ref(false);
const saving = ref(false);
const emptyMessage = ref<Nullable<string>>(null);

const invalidMessages = ref<{
  filename: Nullable<string>;
  text: Nullable<string>;
}>({ filename: null, text: null });

const visible = defineModel<boolean>("visible", {
  required: true,
});

const progress = ref<Nullable<number>>(null);

const isMaximized = ref(false);
const content = ref<Nullable<string>>(null);
const origContent = ref<Nullable<string>>(null);

const filePathName = ref<Nullable<string>>(null);

const heightClass = computed(() =>
  isMaximized.value ? "min-h-[90vh]" : "min-h-[55vh]",
);

const textAreaRef =
  ref<
    Nullable<ComponentPublicInstance<{}, any> & { $el: HTMLTextAreaElement }>
  >(null);

const props = defineProps<{
  path?: string;
  header?: string;
  url?: string;
  saveUrl?: string;
  dir?: Nullable<string>;
}>();

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
const isDisabled = computed(
  () =>
    !!invalidMessages.value.filename ||
    !!invalidMessages.value.text ||
    saving.value ||
    loading.value ||
    origContent.value === content.value,
);

const openPopup = async () => {
  popupStore.isEscapable = false;
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

  await nextTick();
  const inputEl = textAreaRef.value?.$el;
  if (inputEl) {
    inputEl?.focus();
  }
};

const handleSave = async () => {
  if (!props.saveUrl) {
    return;
  }
  try {
    emptyMessage.value = null;
    saving.value = true;
    const data = {
      path: props.path || filePathName.value,
      content: content.value,
      dir: props.dir,
    };
    const response = await axios.put(props.saveUrl, data);

    if (response.data.content) {
      origContent.value = response.data.content;
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
  invalidMessages.value.text = null;
  invalidMessages.value.filename = null;
  filePathName.value = null;
  content.value = null;
  origContent.value = null;
  emptyMessage.value = null;
  popupStore.isEscapable = true;
  progress.value = null;
  emit("after-hide");
};
</script>
