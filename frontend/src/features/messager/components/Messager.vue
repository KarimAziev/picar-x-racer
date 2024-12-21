<template>
  <Messages class="message-wrapper" />
</template>

<script setup lang="ts">
import Messages from "@/features/messager/components/MessageListContainer.vue";
</script>

<style scoped lang="scss">
.message-wrapper {
  position: absolute;
  padding: 0 10px;
  top: 0;
  left: 0;
  overflow-y: scroll;
  height: 40px;
  max-height: 40px;
  max-width: 300px;

  @media (min-width: 992px) {
    max-width: 400px;
  }

  @media (min-height: 768px) and (min-width: 992px) {
    z-index: 1000;
    height: 300px;
    max-height: 300px;
    left: 0;
    font-size: 1rem;
    top: 100px;
  }
}
</style>
