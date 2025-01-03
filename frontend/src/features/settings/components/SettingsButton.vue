<template>
  <MediaControls v-if="isMobile" class="absolute z-12 top-0 left-1">
    <Button
      aria-label="settings"
      variant="text"
      icon="pi pi-cog"
      @click="handleShow"
    />
  </MediaControls>
  <span v-else class="absolute z-12 top-0 left-1">
    <Button
      aria-label="settings"
      variant="text"
      icon="pi pi-cog"
      @click="handleShow"
    />
  </span>
</template>

<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import { usePopupStore } from "@/features/settings/stores";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";

const popupStore = usePopupStore();

const isMobile = useDeviceWatcher();

const MediaControls = defineAsyncComponent({
  loader: () => import("@/ui/MediaControls.vue"),
});

const handleShow = () => {
  popupStore.isOpen = true;
};
</script>
