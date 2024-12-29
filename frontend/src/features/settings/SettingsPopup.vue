<template>
  <MediaControls v-if="isMobile" class="drawer-button">
    <Button severity="secondary" icon="pi pi-bars" @click="handleShow" />
  </MediaControls>
  <Button
    v-else
    severity="secondary"
    icon="pi pi-bars"
    @click="handleShow"
    class="drawer-button"
  />
  <Dialog
    v-model:visible="popupStore.isOpen"
    header="Settings"
    dismissableMask
    modal
    :closable="isClosable"
    :closeOnEscape="isEscapeOnCloseEnabled"
  >
    <Settings />
    <div class="footer">
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
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import { computed, defineAsyncComponent } from "vue";
import Settings from "@/features/settings/Settings.vue";
import { usePopupStore, useSettingsStore } from "@/features/settings/stores";
import { saveableTabs } from "@/features/settings/config";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";

const popupStore = usePopupStore();
const settingsStore = useSettingsStore();
const isSaving = computed(() => settingsStore.saving);
const isSaveDisabled = computed(() => settingsStore.isSaveButtonDisabled());

const isClosable = computed(() => !popupStore.isKeyRecording);
const isMobile = useDeviceWatcher();
const isEscapeOnCloseEnabled = computed(
  () => !popupStore.isKeyRecording && !popupStore.isPreviewImageOpen,
);

const isCurrentTabSaveable = computed(
  () => popupStore.tab && saveableTabs[popupStore.tab],
);

const MediaControls = defineAsyncComponent({
  loader: () => import("@/ui/MediaControls.vue"),
});

const handleHide = () => {
  popupStore.isOpen = false;
};

const handleShow = () => {
  popupStore.isOpen = true;
};

const saveSettings = async () => {
  await settingsStore.saveSettings();
  popupStore.isOpen = false;
};
</script>
<style scoped lang="scss">
.drawer-button {
  position: fixed;
  z-index: 12;
  top: 5px;
  left: 5px;
}

.footer {
  display: flex;
  justify-content: flex-start;
  gap: 1rem;
  margin-top: 2rem;
}
</style>
