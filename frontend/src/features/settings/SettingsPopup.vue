<template>
  <Button
    severity="secondary"
    icon="pi pi-bars"
    @click="store.open = true"
    class="drawer-button"
  />
  <Dialog
    v-model:visible="store.open"
    header="Settings"
    dismissableMask
    closable
    modal
    :closeOnEscape="false"
  >
    <Settings />
    <div class="flex justify-content-end gap-2">
      <Button type="button" label="Close" @click="store.open = false"></Button>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Settings from "@/features/settings/Settings.vue";
import { useSettingsStore } from "@/features/settings/stores";

const store = useSettingsStore();
</script>
<style scoped lang="scss">
.drawer-button {
  position: fixed;
  z-index: 12;
  top: 5px;
  left: 5px;
}
</style>
