<template>
  <div class="flex">
    <div class="flex-1" v-for="(fields, idx) in groups" :key="idx">
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
