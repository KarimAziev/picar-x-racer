<template>
  <div class="settings-wrapper">
    <Settings />
  </div>
</template>

<script setup lang="ts">
import Settings from "@/features/settings/Settings.vue";
</script>

<style>
@media (min-width: 1024px) {
  .settings-wrapper {
    min-height: 100vh;
  }
}
</style>
