<template>
  <ul :class="class">
    <li v-for="message in messages" :key="message.id" class="uppercase text-xs">
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
