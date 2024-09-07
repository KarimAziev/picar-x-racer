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
  max-height: 50%;
  top: 100px;
  left: 0;
  z-index: 1000;
  overflow-y: scroll;
}

.message {
  list-style: none;
  padding: 0;
  text-transform: uppercase;
}

.message-wrapper {
  -ms-overflow-style: none; /* Internet Explorer 10+ */
  scrollbar-width: none; /* Firefox */
}
.message-wrapper::-webkit-scrollbar {
  display: none; /* Safari and Chrome */
}
</style>
