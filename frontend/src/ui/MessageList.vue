<template>
  <ul :class="class">
    <li v-for="message in messages" :key="message.id">
      <RoboText
        :title="message.title"
        :type="message.type"
        :text="message.text"
      />
    </li>
  </ul>
</template>

<script setup lang="ts">
import RoboText from "@/ui/RoboText.vue";
import type { MessageItem } from "@/features/messager";

defineProps<{ class?: string; messages: MessageItem[] }>();
</script>

<style scoped lang="scss">
ul {
  -ms-overflow-style: none; /* Internet Explorer 10+ */
  scrollbar-width: none; /* Firefox */
}
ul::-webkit-scrollbar {
  display: none; /* Safari and Chrome */
}

li {
  list-style: none;
  padding: 0;
  text-transform: uppercase;
  max-width: 200px;
  font-size: 0.8rem;

  @media (min-width: 992px) {
    max-width: 300px;
  }
}
</style>
