<template>
  <Button
    severity="secondary"
    icon="pi pi-bars"
    @click="visible = true"
    class="drawer-button"
  />
  <Dialog
    v-model:visible="visible"
    header="Settings"
    dismissableMask
    closable
    modal
  >
    <Settings />
    <div class="flex justify-content-end gap-2">
      <Button type="button" label="Close" @click="visible = false"></Button>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import Button from "primevue/button";
import { ref } from "vue";
import Dialog from "primevue/dialog";

import Settings from "@/features/settings/Settings.vue";

const visible = ref();
</script>
<style scoped lang="scss">
.drawer-button {
  position: fixed;
  z-index: 12;
  top: 5px;
  left: 5px;
}
</style>
