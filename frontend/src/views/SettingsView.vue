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
    height: calc(var(--app-height));
  }
}
</style>
