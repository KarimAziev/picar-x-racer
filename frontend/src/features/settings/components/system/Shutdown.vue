<template>
  <Button
    @click="confirmShutdown($event)"
    label="Power off"
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

const confirmShutdown = (event: MouseEvent) => {
  confirmDialog.require({
    target: event.currentTarget as HTMLElement,
    message: "Do you really want to power off the whole OS?",
    icon: "pi pi-info-circle",
    rejectProps: {
      label: "Cancel",
      severity: "secondary",
      outlined: true,
    },
    acceptProps: {
      label: "Power off",
      severity: "danger",
    },
    accept: async () => {
      await store.shutdown();
    },
    reject: () => {},
  });
};
</script>
