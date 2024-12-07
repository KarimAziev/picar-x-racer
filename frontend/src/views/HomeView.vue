<template>
  <PreloadMask :loading="true"> </PreloadMask>
  <Controller />
</template>

<script setup lang="ts">
import { onMounted, defineAsyncComponent, watch } from "vue";
import { useRouter } from "vue-router";
import { useSettingsStore, useCameraStore } from "@/features/settings/stores";
import PreloadMask from "@/ui/PreloadMask.vue";

const cameraStore = useCameraStore();

const Controller = defineAsyncComponent({
  loader: () => import("@/features/controller/Controller.vue"),
});

const settingsStore = useSettingsStore();

const router = useRouter();

watch(
  () => settingsStore.data.virtual_mode,
  (value) => {
    if (value) {
      router.push("/virtual");
    } else {
      router.push("/");
    }
  },
);

onMounted(async () => {
  await settingsStore.fetchSettingsInitial();
  await cameraStore.fetchData();
});
</script>
<style scoped lang="scss"></style>
