<template>
  <Dialog
    :header="header"
    v-model:visible="newDirectoryPopupVisible"
    dismissableMask
    content-class="w-[vw] sm:w-[480px]"
    @show="openCreateDirectoryPopup"
    modal
    @after-hide="afterHide"
  >
    <InputText
      @keyup.stop.enter="handleSubmitNewDirectoryPopup"
      @keydown.prevent.stop.esc="handleDiscardNewDirectoryPopup"
      :name="`new-dir`"
      v-model="newDir"
      class="!w-50"
      autofocus
      ref="inputRef"
    />
    <template #footer>
      <div class="flex gap-x-2 mt-2">
        <span class="flex justify-start gap-x-4">
          <Button
            type="button"
            label="Create"
            :disabled="!newDir?.trim().length"
            @click="handleSubmitNewDirectoryPopup"
          ></Button>
          <Button
            type="button"
            outlined
            label="Close"
            @click="handleDiscardNewDirectoryPopup"
          ></Button>
        </span>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { nextTick, ref, ComponentPublicInstance, computed } from "vue";
import InputText from "primevue/inputtext";
import { usePopupStore } from "@/features/settings/stores";

const popupStore = usePopupStore();
const emit = defineEmits(["after-hide", "submit:dir"]);

const newDirectoryPopupVisible = defineModel<boolean>("visible", {
  required: true,
});
const newDir = ref<string>();

const props = defineProps<{
  currentDirectory?: string;
}>();

const inputRef = ref<
  (ComponentPublicInstance<{}, any> & { $el: HTMLInputElement }) | null
>(null);

const header = computed(() =>
  !props.currentDirectory
    ? "Create directory"
    : `Create directory in ${props.currentDirectory}`,
);

const openCreateDirectoryPopup = async () => {
  popupStore.isEscapable = false;
  await nextTick();
  const inputEl = inputRef.value?.$el;
  if (inputEl) {
    inputEl?.focus();
  }
};

const handleSubmitNewDirectoryPopup = async () => {
  const confirmedDir = newDir.value && newDir.value.trim();
  if (confirmedDir && confirmedDir.length > 0) {
    emit("submit:dir", confirmedDir);
    newDir.value = "";
  }
  newDirectoryPopupVisible.value = false;
  afterHide();
};

const handleDiscardNewDirectoryPopup = () => {
  newDir.value = "";
  newDirectoryPopupVisible.value = false;
  afterHide();
};

const afterHide = () => {
  popupStore.isEscapable = true;
  emit("after-hide");
};
</script>
