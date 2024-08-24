<template>
  <ul class="message-wrapper">
    <li class="message" v-for="message in store.messages" :key="message.id">
      <RoboText
        :title="message.title"
        :type="message.type"
        :key="message.id"
        :text="message.text"
      />
    </li>
  </ul>
</template>

<script setup lang="ts">
import RoboText from "@/ui/RoboText.vue";
import { useMessagerStore } from "@/features/messager/store";

const store = useMessagerStore();
</script>

<style scoped lang="scss">
.message-wrapper {
  position: fixed;
  top: 100px;
  left: 0;
  z-index: 1000;
}

.message {
  list-style: none;
  padding: 0;
  text-transform: uppercase;
}
</style>
