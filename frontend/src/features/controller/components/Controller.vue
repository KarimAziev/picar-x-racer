<template>
  <CarModelViewer v-if="isCarModelVisible" />
  <TextInfo v-if="isTextInfoVisible" />
  <Speedometer v-if="isSpeedometerVisible" />
</template>
<script setup lang="ts">
import { useCarController } from "@/features/controller/composable";
import { defineAsyncComponent, computed } from "vue";
import { useSettingsStore } from "@/features/settings/stores";
import { useControllerStore } from "@/features/controller/store";

const settingsStore = useSettingsStore();
const controllerStore = useControllerStore();
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

useCarController();
</script>
