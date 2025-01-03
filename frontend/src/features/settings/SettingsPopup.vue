<template>
  <Dialog
    v-model:visible="popupStore.isOpen"
    header="Settings"
    dismissableMask
    modal
    :closable="isClosable"
    :closeOnEscape="isEscapeOnCloseEnabled"
  >
    <Settings />
    <div class="flex justify-start gap-4 mt-8">
      <Button
        v-if="isCurrentTabSaveable"
        type="button"
        label="Save"
        :disabled="isSaveDisabled"
        :loading="isSaving"
        @click="saveSettings"
      ></Button>
      <Button type="button" outlined label="Close" @click="handleHide"></Button>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Dialog } from "primevue";
import Settings from "@/features/settings/Settings.vue";
import { usePopupStore, useSettingsStore } from "@/features/settings/stores";
import { saveableTabs } from "@/features/settings/config";

const popupStore = usePopupStore();
const settingsStore = useSettingsStore();
const isSaving = computed(() => settingsStore.saving);
const isSaveDisabled = computed(() => settingsStore.isSaveButtonDisabled());

const isClosable = computed(() => !popupStore.isKeyRecording);
const isEscapeOnCloseEnabled = computed(
  () => !popupStore.isKeyRecording && !popupStore.isPreviewImageOpen,
);

const isCurrentTabSaveable = computed(
  () => popupStore.tab && saveableTabs[popupStore.tab],
);

const handleHide = () => {
  popupStore.isOpen = false;
};

const saveSettings = async () => {
  await settingsStore.saveSettings();
  popupStore.isOpen = false;
};
</script>
