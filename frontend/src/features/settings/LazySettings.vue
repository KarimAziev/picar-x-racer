<template>
  <SettingsPopup v-if="storeSettings.loaded" />
</template>

<script setup lang="ts">
import { onMounted, computed, defineAsyncComponent } from "vue";
import { useSettingsStore } from "@/features/settings/stores";

const SettingsPopup = defineAsyncComponent({
  loader: () => import("@/features/settings/SettingsPopup.vue"),
});

const storeSettings = useSettingsStore();
const loaded = computed(() => storeSettings.loaded);

onMounted(() => {
  if (!loaded.value) {
    storeSettings.fetchSettingsInitial();
  }
});
</script>
<style scoped lang="scss"></style>
