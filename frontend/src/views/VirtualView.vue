<template>
  <FullscreenContent>
    <CarModelViewer
      class="flex-auto"
      :zoom="10"
      :rotationY="140"
      :rotationX="-5"
    />
    <GaugesBlock />
  </FullscreenContent>
</template>

<script setup lang="ts">
import { defineAsyncComponent, watch, onBeforeMount } from "vue";
import { useRouter } from "vue-router";
import FullscreenContent from "@/ui/FullscreenContent.vue";
import { useSettingsStore } from "@/features/settings/stores";
import GaugesBlock from "@/features/controller/components/GaugesBlock.vue";

const settingsStore = useSettingsStore();

const router = useRouter();

const CarModelViewer = defineAsyncComponent({
  loader: () =>
    import(
      "@/features/controller/components/CarModelViewer/CarModelViewer.vue"
    ),
});

watch(
  () => settingsStore.data.general.virtual_mode,
  (value) => {
    if (!value) {
      router.push("/");
    }
  },
);

onBeforeMount(() => {
  if (!settingsStore.data.general.virtual_mode) {
    settingsStore.data.general.virtual_mode = true;
  }
});
</script>
