<template>
  <span v-if="connected" class="bold">{{ clients }}</span>
  <DisconnectedIndicator v-else />
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import { useAppSyncStore } from "@/features/syncer";

const syncStore = useAppSyncStore();

const DisconnectedIndicator = defineAsyncComponent({
  loader: () => import("@/features/syncer/components/DisconnectIndicator.vue"),
});

const connected = computed(() => syncStore.model?.connected);

const clients = computed(
  () =>
    `${syncStore.active_connections} CONNECTION${syncStore.active_connections === 1 ? "" : "S"}`,
);
</script>
