<template>
  <slot v-if="isEnabled"></slot>
</template>
<script setup lang="ts">
import { computed } from "vue";
import { useStore } from "@/features/settings/stores/settings";

import { ToggleableKey } from "@/features/settings/interface";
import { getObjProp } from "@/util/obj";

export type Props = { setting: ToggleableKey };

const props = defineProps<Props>();

const settingsStore = useStore();

const isEnabled = computed(
  () => settingsStore.loaded && getObjProp(props.setting, settingsStore.data),
);
</script>
