<template>
  <span :class="className" ref="elem">
    <span class="title" v-if="title">{{ title }} &nbsp;</span>
    <span class="text">{{ msg }}</span>
    <samp v-if="isCaretVisible" class="caret" />
  </span>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";

const props = defineProps<{
  text?: string;
  type?: "error" | "info" | "success" | "warning";
  title?: string;
}>();

const classes = {
  info: "color-primary",
  success: "color-primary",
  warning: "color-warning",
  error: "color-error",
};

const className = computed(() => (props.type ? classes[props.type] : ""));

const msg = ref("");
const elem = ref<HTMLElement | null>();
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

onMounted(() => {
  typeText();
  elem.value?.scrollIntoView({ behavior: "smooth", block: "end" });
});
</script>

<style scoped lang="scss">
.caret {
  border: 1px solid currentColor;
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

.title {
  font-weight: 800;
}
.text {
  font-weight: 700;
}
</style>
