<template>
  <Messages class="message-wrapper" />
</template>

<script setup lang="ts">
import Messages from "@/features/messager/components/MessageListContainer.vue";
</script>

<style scoped lang="scss">
.message-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  overflow-y: scroll;
  height: 40px;
  max-height: 40px;

  @media (min-height: 768px) and (min-width: 992px) {
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
