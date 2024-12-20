<template>
  <Button
    @click="handleConfirm($event)"
    label="Reboot"
    severity="danger"
    outlined
    v-tooltip="
      'This will restart the entire operating system and may interrupt any ongoing operations.'
    "
  ></Button>
  <ConfirmPopup></ConfirmPopup>
</template>

<script setup lang="ts">
import ConfirmPopup from "primevue/confirmpopup";
import { useSettingsStore } from "@/features/settings/stores";
import { useShutdownHandler } from "@/features/settings/composables/useShutdownHandler";

const settingsStore = useSettingsStore();

const { handleConfirm } = useShutdownHandler({
  message:
    "Are you sure you want to restart the system? This will interrupt any ongoing operations.",
  onAccept: settingsStore.restart,
  acceptProps: {
    label: "Reboot Now",
  },
});
</script>
