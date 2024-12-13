<template>
  <MessageList :messages="store.messages" :class="props.class" />
</template>

<script setup lang="ts">
import MessageList from "@/ui/MessageList.vue";
import { useMessagerStore } from "@/features/messager";

const props = defineProps<{ class?: string }>();

const store = useMessagerStore();
</script>
