<template>
  <div :class="classObject" class="active_connections">{{ clients }}</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useAppSyncStore } from "@/features/syncer";

const syncStore = useAppSyncStore();

const classObject = computed(() => ({
  ["disconnected"]: !syncStore.model?.connected,
  ["blink"]: !syncStore.model?.connected,
}));

const clients = computed(() =>
  syncStore.model?.connected
    ? `CONNECTED ${syncStore.active_connections} CLIENT${syncStore.active_connections === 1 ? "" : "S"}`
    : "DISCONNECTED",
);
</script>

<style scoped lang="scss">
@use "@/assets/scss/blink";

.active_connections {
  font-weight: bold;
  position: fixed;
  font-size: 10px;
  right: 2px;
  top: 1px;
  z-index: 12;
}
.disconnected {
  color: var(--color-red);
}
</style>
