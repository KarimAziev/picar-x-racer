<template>
  <div class="wrapper">
    <div class="column">
      <div class="col-title">Visibility</div>
      <ToggleFields :fields="visibilitySettings" :store="store" />
    </div>
    <div class="column">
      <div class="col-title">Misc</div>
      <ToggleFields :fields="behaviorSettings" :store="store" />
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import {
  behaviorSettings,
  visibilitySettings,
} from "@/features/settings/config";
import ToggleFields from "@/ui/ToggleFields.vue";

const store = useSettingsStore();
</script>
<style scoped lang="scss">
@use "@/assets/scss/two-column-layout.scss";
</style>
