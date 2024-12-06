<template>
  <div class="active_connections">{{ clients }}</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useAppSyncStore } from "@/features/syncer/store";

const syncStore = useAppSyncStore();

const clients = computed(
  () =>
    `CONNECTED ${syncStore.active_connections} CLIENT${syncStore.active_connections === 1 ? "" : "S"}`,
);
</script>

<style scoped lang="scss">
.active_connections {
  font-weight: bold;
  position: fixed;
  font-size: 10px;
  right: 2px;
  top: 10px;
  z-index: 12;
}
</style>
