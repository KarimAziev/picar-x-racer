<template>
  <div class="message-wrapper">
    <div
      class="message"
      v-for="message in store.messages"
      :key="message.id"
      :class="message.type"
    >
      <RoboText :key="message.id">{{ message.text }}</RoboText>
    </div>
  </div>
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
  left: 20px;
  z-index: 1000;
}

.message {
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 10px;
}

.message.success {
  color: var(--robo-color-primary);
}

.message.info {
  color: var(--robo-color-primary);
}

.message.error {
  color: var(red);
}
</style>
