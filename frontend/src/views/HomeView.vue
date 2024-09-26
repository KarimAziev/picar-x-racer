<template>
  <PreloadMask :loading="true"> </PreloadMask>
  <CarController />
</template>

<script setup lang="ts">
import { onMounted, defineAsyncComponent, watch } from "vue";
import { useRouter } from "vue-router";
import { useSettingsStore, useCameraStore } from "@/features/settings/stores";
import PreloadMask from "@/ui/PreloadMask.vue";

const cameraStore = useCameraStore();
const CarController = defineAsyncComponent({
  loader: () => import("@/features/controller/CarController.vue"),
});

const settingsStore = useSettingsStore();

const router = useRouter();

watch(
  () => settingsStore.settings.virtual_mode,
  (value) => {
    if (value) {
      router.push("/virtual");
    }
  },
);

onMounted(async () => {
  await cameraStore.fetchConfig();
  await settingsStore.fetchSettingsInitial();
});
</script>
<style scoped lang="scss"></style>
