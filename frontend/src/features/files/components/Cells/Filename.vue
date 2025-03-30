<template>
  <Cell class="truncate relative block justify-end" ref="wrapperElement">
    <div
      v-if="renaming && !disabled"
      class="flex items-center gap-2 relative justify-end justify-self-end"
    >
      <InputText
        class="!max-w-[90%] !w-[90%]"
        @keyup.stop.enter="handleSubmitRename(path, newName.trim())"
        @keydown.prevent.stop.esc="handleDiscardRename"
        :name="`rename-${path}`"
        v-model="newName"
        @blur="handleBlur"
        autofocus
        ref="inputRef"
      />
      <Button
        class="!w-[12px]"
        icon="pi pi-times"
        text
        v-tooltip="'Discard'"
        severity="danger"
        @click="handleDiscardRename"
      />
      <Button
        class="!w-[12px]"
        icon="pi pi-check"
        text
        severity="success"
        v-tooltip="'Save'"
        :disabled="newName.trim() === name"
        @click="handleSubmitRename(path, newName.trim())"
      />
    </div>
    <div
      v-else
      class="w-full block truncate"
      v-tooltip="name"
      @click="startRename"
    >
      {{ name }}
    </div>
    <ButtonIcon
      v-if="isHovered && !renaming && !isUploadingRow"
      rounded
      v-tooltip="'Rename'"
      severity="secondary"
      class="absolute bottom-0 right-0"
      text
      icon="pi pi-pencil"
      @click="startRename"
    ></ButtonIcon>
  </Cell>
</template>

<script setup lang="ts">
import {
  nextTick,
  computed,
  ref,
  ComponentPublicInstance,
  useTemplateRef,
} from "vue";
import InputText from "primevue/inputtext";
import { useElementHover } from "@vueuse/core";
import { isNumber } from "@/util/guards";
import type { UploadingFileDetail } from "@/features/files/interface";

import ButtonIcon from "@/ui/ButtonIcon.vue";
import Cell from "@/features/files/components/Cell.vue";

const wrapperElement = useTemplateRef<HTMLButtonElement>("wrapperElement");
const isHovered = useElementHover(wrapperElement);

export interface Props
  extends Pick<UploadingFileDetail, "path" | "name" | "progress"> {
  disabled?: boolean;
}
const props = defineProps<Props>();
const newName = ref(props.name);
const renaming = ref(false);

const isUploadingRow = computed(() => isNumber(props.progress));

const handleBlur = () => {
  if (props.name === newName.value) {
    handleDiscardRename();
  }
};

const inputRef = ref<
  (ComponentPublicInstance<{}, any> & { $el: HTMLInputElement }) | null
>(null);
const emit = defineEmits(["rename"]);

const handleDiscardRename = () => {
  renaming.value = false;
  newName.value = props.name;
};

const startRename = async () => {
  if (isUploadingRow.value) {
    return;
  }
  renaming.value = true;
  newName.value = props.name;
  await nextTick();
  const inputEl = inputRef.value?.$el;
  if (inputRef.value) {
    inputEl?.focus();
  }
};

const handleSubmitRename = (path: string, newName: string) => {
  renaming.value = false;
  emit("rename", path, newName);
};
</script>

<style scoped lang="scss"></style>
