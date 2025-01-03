<template>
  <div class="flex">
    <div class="flex-1" v-for="(fields, idx) in groups" :key="idx">
      <ToggleFields scope="general" :fields="fields" :store="store" />
      <component
        v-for="(comp, i) in extraComponents[
          idx as keyof typeof extraComponents
        ]"
        :key="i"
        :is="comp"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import { generalSwitchSettings } from "@/features/settings/config";
import ToggleFields from "@/ui/ToggleFields.vue";
import { splitObjIntoGroups } from "@/util/obj";
import FPSToggle from "@/features/settings/components/camera/FPSToggle.vue";
import DarkThemeSwitch from "@/features/settings/components/theming/DarkThemeSwitch.vue";

const groups = splitObjIntoGroups(2, generalSwitchSettings);

const extraComponents = {
  0: [FPSToggle],
  1: [DarkThemeSwitch],
};

const store = useSettingsStore();
</script>
