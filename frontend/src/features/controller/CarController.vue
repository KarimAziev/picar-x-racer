<template>
  <div class="wrapper">
    <div class="content" v-if="!isSettingsOpened">
      <VideoBox />
    </div>
    <div class="right" v-if="loaded">
      <CarModelViewer
        v-if="isCarModelVisible && !isVirtualMode"
        :width="300"
        :height="300"
      />
      <TextInfo v-if="isTextInfoVisible" />
      <Speedometer v-if="isSpeedometerVisible" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import { usePopupStore } from "@/features/settings/stores";
import { useCarController } from "@/features/controller/composable";
import { useSettingsStore } from "@/features/settings/stores";
import { useControllerStore } from "@/features/controller/store";

const settingsStore = useSettingsStore();
const controllerStore = useControllerStore();
const popupStore = usePopupStore();
const isVirtualMode = computed(() => settingsStore.settings.virtual_mode);
const isSettingsOpened = computed(() => popupStore.isOpen);
const loaded = computed(() => settingsStore.loaded);

const isTextInfoVisible = computed(
  () =>
    !controllerStore.avoidObstacles && settingsStore.settings.text_info_view,
);
const isSpeedometerVisible = computed(
  () =>
    !controllerStore.avoidObstacles && settingsStore.settings.speedometer_view,
);
const isCarModelVisible = computed(
  () =>
    !controllerStore.avoidObstacles && settingsStore.settings.car_model_view,
);

const CarModelViewer = defineAsyncComponent({
  loader: () =>
    import(
      "@/features/controller/components/CarModelViewer/CarModelViewer.vue"
    ),
});

const TextInfo = defineAsyncComponent({
  loader: () => import("@/features/controller/components/TextInfo.vue"),
});

const Speedometer = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Speedometer.vue"),
});

const VideoBox = defineAsyncComponent({
  loader: () => import("@/features/controller/components/VideoBox.vue"),
});

useCarController(controllerStore, settingsStore, popupStore);
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
</style>
