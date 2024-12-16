<template>
  <slot v-if="isEnabled"></slot>
</template>
<script setup lang="ts">
import { computed } from "vue";
import { useStore } from "@/features/settings/stores/settings";
import { useControllerStore } from "@/features/controller/store";
import { ToggleableKey } from "@/features/settings/interface";
import { getObjProp } from "@/util/obj";

export type Props = { setting: ToggleableKey };

const props = defineProps<Props>();

const settingsStore = useStore();
const controllerStore = useControllerStore();
const isEnabled = computed(
  () =>
    settingsStore.loaded &&
    !controllerStore.avoidObstacles &&
    getObjProp(props.setting, settingsStore.data),
);
</script>
