<template>
  <div class="fullscreen-content" :class="class">
    <slot></slot>
  </div>
</template>
<script setup lang="ts">
defineProps<{ class?: string }>();
</script>

<style scoped lang="scss">
.fullscreen-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  height: calc(var(--app-height));
}
</style>
