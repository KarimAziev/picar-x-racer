<template>
  <Button
    @click="confirmRestart($event)"
    label="Restart"
    severity="danger"
    outlined
  ></Button>
  <ConfirmPopup></ConfirmPopup>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";

import { useConfirm } from "primevue/useconfirm";
import ConfirmPopup from "primevue/confirmpopup";

const confirmDialog = useConfirm();
const store = useSettingsStore();

const confirmRestart = (event: MouseEvent) => {
  confirmDialog.require({
    target: event.currentTarget as HTMLElement,
    message: "Do you really want to restart the whole OS?",
    icon: "pi pi-exclamation-triangle",
    rejectProps: {
      label: "Cancel",
      severity: "secondary",
      outlined: true,
    },
    acceptProps: {
      label: "Restart now",
      severity: "danger",
    },
    accept: async () => {
      await store.restart();
    },
    reject: () => {},
  });
};
</script>
