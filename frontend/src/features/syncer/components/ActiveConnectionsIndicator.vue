<template>
  <Badge
    :value="clientsCount"
    :icon="icon"
    v-tooltip="tooltipText"
    v-if="connected"
  />
  <DisconnectIndicator v-else />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useAppSyncStore } from "@/features/syncer";
import DisconnectIndicator from "@/features/syncer/components/DisconnectIndicator.vue";
import Badge from "@/ui/Badge.vue";

const syncStore = useAppSyncStore();

const connected = computed(() => syncStore.model?.connected);

const clientsCount = computed(() => syncStore.active_connections);

const icon = computed(
  () => `pi-user${syncStore.active_connections === 1 ? "" : "s"}`,
);

const tooltipText = computed(
  () =>
    `${syncStore.active_connections} connected user${syncStore.active_connections === 1 ? "" : "s"}`,
);
</script>
