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
li {
  text-transform: uppercase;
  font-size: 0.8rem;
}
</style>
