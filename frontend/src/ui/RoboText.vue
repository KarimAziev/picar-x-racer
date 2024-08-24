<template>
  <span :class="type">
    <span class="title" v-if="title">{{ title }} &nbsp;</span>
    <span class="text">{{ msg }}</span>
    <samp v-if="isCaretVisible" class="caret" />
  </span>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { wait } from "@/util/wait";

const props = defineProps<{
  text?: string;
  type?: "error" | "info" | "success";
  title?: string;
}>();

const msg = ref("");
const isCaretVisible = ref(true);
const title = ref("");

const typeTitle = async () => {
  if (props.title) {
    for (let i = 0; props.title.length > i; i++) {
      title.value += `${props.title[i]}`;
      await wait(10);
    }
  }
};
const typeText = async () => {
  if (props.title) {
    await typeTitle();
  }
  if (props.text) {
    for (let i = 0; props.text.length > i; i++) {
      msg.value += `${props.text[i]}`;
      await wait(10);
    }
  }
  await wait(200);
  isCaretVisible.value = false;
};

onMounted(typeText);
</script>

<style scoped lang="scss">
.typed {
  white-space: nowrap;
}
.caret {
  border: 1px solid var(--color-text);
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}

.success {
  color: var(--color-text);
}

.info {
  color: var(--color-text);
}

.error {
  color: var(--color-red);
  .caret {
    border: 1px solid var(--color-red);
  }
}
.title {
  font-weight: 800;
}
.text {
  font-weight: 800;
}
</style>
