<template>
  <div class="typed"><slot></slot></div>
</template>

<script setup lang="ts"></script>

<style scoped lang="scss">
@import "@/assets/animation.scss";
.typed {
  overflow: hidden;
  white-space: nowrap;
  animation:
    typing 0.5s steps(30, end),
    blink-caret 0.5s steps(1, end) reverse;
  border-right: 3px solid transparent;
}
.typed::after {
  content: "";
  width: 0;
  overflow: hidden;
  animation: hide-caret 0s steps(30, end) forwards 2s;
}
</style>
