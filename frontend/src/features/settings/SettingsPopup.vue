<template>
  <Button
    severity="secondary"
    icon="pi pi-bars"
    @click="popupStore.isOpen = true"
    class="drawer-button"
  />
  <Dialog
    v-model:visible="popupStore.isOpen"
    header="Settings"
    dismissableMask
    modal
    :closable="!popupStore.isKeyRecording"
    :closeOnEscape="!popupStore.isKeyRecording"
  >
    <Settings />
    <div class="flex justify-content-end gap-2">
      <Button
        type="button"
        label="Close"
        @click="popupStore.isOpen = false"
      ></Button>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Settings from "@/features/settings/Settings.vue";
import { usePopupStore } from "@/features/settings/stores";

const popupStore = usePopupStore();
</script>
<style scoped lang="scss">
.drawer-button {
  position: fixed;
  z-index: 12;
  top: 5px;
  left: 5px;
}
.p-dialog {
  color: var(--color-text);
  font-family: var(--font-family);
}
</style>
