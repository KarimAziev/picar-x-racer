<template>
  <div class="wrapper">
    <div class="column" v-for="(fields, idx) in groups" :key="idx">
      <ToggleFields scope="general" :fields="fields" :store="store" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import { generalSwitchSettings } from "@/features/settings/config";
import ToggleFields from "@/ui/ToggleFields.vue";
import { splitObjIntoGroups } from "@/util/obj";

const groups = splitObjIntoGroups(2, generalSwitchSettings);

const store = useSettingsStore();
</script>
<style scoped lang="scss">
@use "@/assets/scss/two-column-layout.scss";
</style>
