<template>
  <MessageList :messages="store.messages" />
</template>

<script setup lang="ts">
import MessageList from "@/ui/MessageList.vue";
import { useMessagerStore } from "@/features/messager";

const store = useMessagerStore();
</script>
