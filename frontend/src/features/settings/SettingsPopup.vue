<template>
  <Button
    severity="secondary"
    icon="pi pi-bars"
    v-tooltip="'Open settings'"
    @click="popupStore.isOpen = true"
    class="drawer-button"
  />
  <Dialog
    v-model:visible="popupStore.isOpen"
    header="Settings"
    dismissableMask
    modal
    :closable="!popupStore.isKeyRecording"
    :closeOnEscape="
      !popupStore.isKeyRecording && !popupStore.isPreviewImageOpen
    "
  >
    <Settings />
    <div class="footer">
      <Button
        type="button"
        label="Save"
        :loading="isSaving"
        @click="saveSettings"
      ></Button>
      <Button
        type="button"
        outlined
        label="Close"
        @click="popupStore.isOpen = false"
      ></Button>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import { computed } from "vue";
import Settings from "@/features/settings/Settings.vue";
import { usePopupStore, useSettingsStore } from "@/features/settings/stores";

const popupStore = usePopupStore();
const settingsStore = useSettingsStore();
const isSaving = computed(() => settingsStore.saving);

const saveSettings = () => {
  settingsStore.saveSettings();
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
