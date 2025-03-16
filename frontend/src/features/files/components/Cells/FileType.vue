<template>
  <Cell>
    <ButtonIcon
      v-if="isDirectoryType(type)"
      icon="pi pi-folder"
      class="text-xl"
      @click="handleUpdateDir(path)"
    />
    <Photo
      v-else-if="makeImagePreviewURL && isImageType(type)"
      :src="makeImagePreviewURL(path)"
      className="w-10"
      @click="handleOpenImage(path)"
    />
    <Photo
      className="w-10"
      v-else-if="makeVideoPreviewURL && isVideoType(type)"
      :src="makeVideoPreviewURL(path)"
      fallbackIconClass="pi pi-play cursor-pointer"
      @click="handleOpenVideo(path)"
      :caption="`${isNumber(duration) ? secondsToReadableString(duration) : ''}`"
    ></Photo>
    <ButtonIcon
      v-else-if="isTextFile(type)"
      @click="handleOpenText"
      icon="pi pi-align-left"
    ></ButtonIcon>
    <i
      v-else-if="isLoadable(type)"
      class="pi pi-spinner-dotted"
      v-tooltip="'Loadable model'"
    />
    <i v-else class="pi pi-file" />
  </Cell>
</template>

<script setup lang="ts">
import Photo from "@/ui/Photo.vue";
import { isNumber } from "@/util/guards";
import { secondsToReadableString } from "@/util/time";
import type {
  UploadingFileDetail,
  GroupedFile,
} from "@/features/files/interface";
import ButtonIcon from "@/ui/ButtonIcon.vue";
import {
  isVideoType,
  isImageType,
  isDirectoryType,
  isTextFile,
  isLoadable,
} from "@/features/files/components/util";
import Cell from "@/features/files/components/Cell.vue";

export interface Props
  extends Pick<UploadingFileDetail, "type" | "path" | "duration"> {
  makeImagePreviewURL?: (path: GroupedFile["path"]) => string;
  makeVideoPreviewURL?: (path: GroupedFile["path"]) => string;
}
defineProps<Props>();

const emit = defineEmits([
  "update:dir",
  "trigger:image",
  "trigger:video",
  "trigger:text",
]);

const handleUpdateDir = (path: string) => {
  emit("update:dir", path);
};

const handleOpenImage = (path: string) => {
  emit("trigger:image", path);
};

const handleOpenVideo = (path: string) => {
  emit("trigger:video", path);
};

const handleOpenText = (path: string) => {
  emit("trigger:text", path);
};
</script>
