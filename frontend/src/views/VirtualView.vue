<template>
  <FullscreenContent>
    <CarModelViewer
      class="content"
      :zoom="10"
      :rotationY="140"
      :rotationX="-5"
    />
    <GaugesBlock />
  </FullscreenContent>
</template>

<script setup lang="ts">
import {
  onMounted,
  onBeforeUnmount,
  defineAsyncComponent,
  watch,
  onBeforeMount,
} from "vue";
import { useRouter } from "vue-router";
import FullscreenContent from "@/ui/FullscreenContent.vue";
import { useSettingsStore, usePopupStore } from "@/features/settings/stores";

import { useController } from "@/features/controller/composable";
import { useControllerStore } from "@/features/controller/store";
import GaugesBlock from "@/features/controller/components/GaugesBlock.vue";

const settingsStore = useSettingsStore();
const popupStore = usePopupStore();
const controllerStore = useControllerStore();
const {
  addKeyEventListeners,
  removeKeyEventListeners,
  connectWS,
  cleanupGameLoop,
  gameLoop,
  cleanup,
} = useController(controllerStore, settingsStore, popupStore);

const router = useRouter();

const CarModelViewer = defineAsyncComponent({
  loader: () =>
    import(
      "@/features/controller/components/CarModelViewer/CarModelViewer.vue"
    ),
});

watch(
  () => settingsStore.data.virtual_mode,
  (value) => {
    if (!value) {
      router.push("/");
    }
  },
);

onBeforeMount(() => {
  if (!settingsStore.data.virtual_mode) {
    settingsStore.data.virtual_mode = true;
  }
});

onMounted(() => {
  connectWS();
  addKeyEventListeners();
  gameLoop();
});
onBeforeUnmount(() => {
  cleanupGameLoop();
  removeKeyEventListeners();
  cleanup();
});
</script>
<style scoped lang="scss">
.wrapper {
  width: 100%;
  display: flex;
}

.content {
  flex: auto;
}
.right {
  position: absolute;
  right: 0;
  width: 400px;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 1rem 0;
  justify-content: space-between;
  align-items: center;
}

.car-model {
  height: 50vh;
  position: fixed;
}
</style>
