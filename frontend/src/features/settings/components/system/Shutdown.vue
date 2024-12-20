<template>
  <Button
    @click="handleConfirm($event)"
    label="Power Off"
    icon="pi pi-power-off"
    severity="danger"
    outlined
    v-tooltip="
      'This will shut down the entire system. Save all work, as a manual reboot will be required to power it back on.'
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
  message: "Are you sure you want to shut down the entire system?",
  onAccept: settingsStore.shutdown,
  acceptProps: {
    label: "Shut Down",
  },
});
</script>
