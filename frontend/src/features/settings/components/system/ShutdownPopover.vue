<template>
  <Button
    @click="handleTogglePopover"
    icon="pi pi-power-off"
    aria-label="shutdown-reboot"
    variant="text"
    size="small"
    rounded
    v-tooltip="'Shutdown/Reboot'"
  ></Button>
  <Popover ref="popoverRef">
    <div class="flex flex-col gap-1">
      <Button
        :loading="loading"
        @click="handleReboot"
        label="Restart"
        severity="danger"
        variant="text"
        v-tooltip="
          'This will restart the entire operating system and may interrupt any ongoing operations.'
        "
      ></Button>
      <Button
        :loading="loading"
        @click="handleShutdown"
        label="Power Off"
        severity="danger"
        variant="text"
        v-tooltip="
          'This will shut down the entire system. Save all work, as a manual reboot will be required to power it back on.'
        "
      ></Button>
    </div>
  </Popover>
</template>

<script setup lang="ts">
import { ref } from "vue";
import Popover from "primevue/popover";
import type { PopoverMethods } from "primevue/popover";
import { useControllerStore } from "@/features/controller/store";
import { useSettingsStore } from "@/features/settings/stores";

const settingsStore = useSettingsStore();
const controllerStore = useControllerStore();
const loading = ref(false);
const popoverRef = ref<PopoverMethods>();

const handleTogglePopover = (event: Event) => {
  popoverRef.value?.toggle(event);
};

const hidePopover = () => {
  popoverRef.value?.hide();
};

const handleShutdown = async () => {
  loading.value = true;
  controllerStore.resetAll();
  await settingsStore.shutdown();
  loading.value = false;
  hidePopover();
};

const handleReboot = async () => {
  loading.value = true;
  controllerStore.resetAll();
  await settingsStore.restart();
  loading.value = false;
  hidePopover();
};
</script>
<style scoped lang="scss">
button {
  color: inherit;
}
</style>
