<template>
  <SettingsPopup />
  <RouterView />
  <Toast />
</template>

<script setup lang="ts">
import { RouterView } from "vue-router";
import Toast from "primevue/toast";
import SettingsPopup from "@/features/settings/SettingsPopup.vue";
</script>
