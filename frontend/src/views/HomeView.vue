<template>
  <PreloadMask :loading="true"> </PreloadMask>
  <Controller />
</template>

<script setup lang="ts">
import { defineAsyncComponent, watch } from "vue";
import { useRouter } from "vue-router";
import { useSettingsStore } from "@/features/settings/stores";
import PreloadMask from "@/ui/PreloadMask.vue";

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
</script>
<style scoped lang="scss"></style>
