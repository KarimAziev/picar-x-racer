<template>
  <span v-if="connected" class="bold">{{ clients }}</span>
  <DisconnectIndicator v-else />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useAppSyncStore } from "@/features/syncer";
import DisconnectIndicator from "@/features/syncer/components/DisconnectIndicator.vue";

const syncStore = useAppSyncStore();

const connected = computed(() => syncStore.model?.connected);

const clients = computed(
  () =>
    `${syncStore.active_connections} CONNECTION${syncStore.active_connections === 1 ? "" : "S"}`,
);
</script>
