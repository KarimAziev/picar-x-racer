<template>
  <MessageList :messages="store.messages" class="message-wrapper" />
</template>

<script setup lang="ts">
import MessageList from "@/ui/MessageList.vue";
import { useMessagerStore } from "@/features/messager/store";

const store = useMessagerStore();
</script>

<style scoped lang="scss">
.message-wrapper {
  position: absolute;
  top: 0%;
  overflow-y: scroll;
  height: 20px;
  max-height: 20px;

  @media (min-width: 1200px) and (orientation: landscape) {
    height: 200px;
    max-height: 200px;
    left: 0;
    z-index: 1000;
    font-size: 0.8rem;
    top: 50%;
    max-height: 50%;
    font-size: 1rem;
    top: 100px;
  }
}
</style>
