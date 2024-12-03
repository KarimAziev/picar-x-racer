<template>
  <slot v-if="isEnabled"></slot>
</template>
<script setup lang="ts">
import { computed } from "vue";
import {
  ToggleableSettings,
  useStore,
} from "@/features/settings/stores/settings";
import { useControllerStore } from "@/features/controller/store";

export type Props = { setting: keyof ToggleableSettings };

const props = defineProps<Props>();

const settingsStore = useStore();
const controllerStore = useControllerStore();

const isEnabled = computed(
  () =>
    settingsStore.loaded &&
    !controllerStore.avoidObstacles &&
    settingsStore.data[props.setting],
);
</script>
