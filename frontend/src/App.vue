<template>
  <SettingsPopup />
  <RouterView />
</template>

<script setup lang="ts">
import { RouterView } from "vue-router";
import SettingsPopup from "@/features/settings/SettingsPopup.vue";
</script>
