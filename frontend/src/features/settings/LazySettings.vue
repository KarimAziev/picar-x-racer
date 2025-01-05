<template>
  <SettingsPopup v-if="loaded" />
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import { useSettingsStore } from "@/features/settings/stores";

const SettingsPopup = defineAsyncComponent({
  loader: () => import("@/features/settings/SettingsPopup.vue"),
});

const storeSettings = useSettingsStore();
const loaded = computed(() => storeSettings.loaded);
</script>
