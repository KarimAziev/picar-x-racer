<template>
  <PreloadMask :loading="true"> </PreloadMask>
  <CarController />
</template>

<script setup lang="ts">
import { onMounted, computed, defineAsyncComponent, watch } from "vue";
import { useRouter } from "vue-router";
import { useSettingsStore } from "@/features/settings/stores";
import PreloadMask from "@/ui/PreloadMask.vue";

const CarController = defineAsyncComponent({
  loader: () => import("@/features/controller/CarController.vue"),
});

const settingsStore = useSettingsStore();
const loaded = computed(() => settingsStore.loaded);

const router = useRouter();

watch(
  () => settingsStore.settings.virtual_mode,
  (value) => {
    if (value) {
      router.push("/virtual");
    }
  },
);

onMounted(() => {
  if (!loaded.value) {
    settingsStore.fetchSettingsInitial();
  }
});
</script>
<style scoped lang="scss"></style>
