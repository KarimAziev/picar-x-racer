<template>
  <Button
    icon="pi pi-microphone"
    rounded
    @click="handlePopupOpen"
    :disabled="popupStore.isOpen"
    text
  />
</template>

<script setup lang="ts">
import Button from "primevue/button";
import { usePopupStore } from "@/features/settings/stores";
import { SettingsTab } from "@/features/settings/enums";

const popupStore = usePopupStore();

const handlePopupOpen = () => {
  popupStore.tab = SettingsTab.TTS;
  popupStore.isOpen = true;
};
</script>
