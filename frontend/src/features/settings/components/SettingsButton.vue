<template>
  <MediaControls v-if="isMobile" class="absolute z-12 top-0 left-1">
    <Button
      aria-label="settings"
      variant="text"
      icon="pi pi-cog"
      @click="handleShow"
    />
    <GoToAutonomyButton />
  </MediaControls>
  <span v-else class="absolute z-12 top-0 left-1">
    <Button
      aria-label="settings"
      variant="text"
      icon="pi pi-cog"
      @click="handleShow"
    />
    <GoToAutonomyButton />
  </span>
</template>

<script setup lang="ts">
import { defineAsyncComponent, inject } from "vue";
import { usePopupStore } from "@/features/settings/stores";
import type { Ref } from "vue";

const isMobile = inject<Ref<boolean, boolean>>("isMobile");

const popupStore = usePopupStore();

const MediaControls = defineAsyncComponent({
  loader: () => import("@/ui/MediaControls.vue"),
});

const GoToAutonomyButton = defineAsyncComponent({
  loader: () => import("@/features/autonomy/components/GoToAutonomyButton.vue"),
});

const handleShow = () => {
  popupStore.isOpen = true;
};
</script>
