<template>
  <div class="preloader-wrapper" v-if="showPreloader">
    <div
      class="preloader"
      v-for="(text, index) in visibleMessages"
      :key="index"
    >
      <RoboText>{{ text }}</RoboText>
    </div>
  </div>
  <slot v-else></slot>
</template>

<script setup lang="ts">
import { ref } from "vue";
import RoboText from "@/ui/RoboText.vue";

const props = defineProps<{ loading?: boolean; delay?: number }>();

const showPreloader = ref(true);
const allMessages = ["LOAD RASPBERRY", "MEMORY SET", "SYSTEM STATUS", "OK_"];
const visibleMessages = ref<string[]>([]);

const delayDuration = props.delay ?? 500; // in ms

let messageIndex = 0;
let delayTimeout: ReturnType<typeof setTimeout> | null = null;

const showNextMessage = () => {
  if (messageIndex < allMessages.length) {
    visibleMessages.value.push(allMessages[messageIndex]);
    messageIndex++;
    delayTimeout = setTimeout(showNextMessage, delayDuration);
  } else {
    showPreloader.value = false;
    if (delayTimeout) {
      clearTimeout(delayTimeout);
    }
  }
};

if (props.loading) {
  showNextMessage();
}
</script>

<style scoped lang="scss">
.preloader-wrapper {
  position: absolute;
  text-align: left;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  height: 100%;
  display: flex;
  justify-content: center;
  flex-direction: column;
}

.preloader {
  display: flex;
  align-items: center;
  margin: 0 auto;
}
</style>
