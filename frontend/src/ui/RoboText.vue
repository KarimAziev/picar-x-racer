<template>
  <span :class="type">
    <span class="title" v-if="title">{{ title }} &nbsp;</span>
    <span class="text">{{ msg }}</span>
    <samp v-if="isCaretVisible" class="caret" />
  </span>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";

const props = defineProps<{
  text?: string;
  type?: "error" | "info" | "success";
  title?: string;
}>();

const msg = ref("");
const isCaretVisible = ref(true);
const title = ref("");

const typeTitle = () => {
  return new Promise<void>((resolve) => {
    if (!props.title) {
      return resolve();
    }

    let index = 0;

    const typeNextChar = () => {
      if (!props.title) {
        return;
      }
      if (index < props.title.length) {
        title.value += props.title[index++];
        requestAnimationFrame(typeNextChar);
      } else {
        resolve();
      }
    };

    typeNextChar();
  });
};

const typeText = () => {
  typeTitle().then(() => {
    if (!props.text) return;

    let index = 0;

    const typeNextChar = () => {
      if (!props.text) {
        return;
      }
      if (index < props.text.length) {
        msg.value += props.text[index++];
        requestAnimationFrame(typeNextChar);
      } else {
        setTimeout(() => {
          isCaretVisible.value = false;
        }, 200);
      }
    };

    typeNextChar();
  });
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
