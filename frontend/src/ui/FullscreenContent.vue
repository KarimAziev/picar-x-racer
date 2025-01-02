<template>
  <div
    class="fullscreen-content flex flex-col items-center justify-center relative"
    :class="class"
  >
    <slot></slot>
  </div>
</template>
<script setup lang="ts">
defineProps<{ class?: string }>();
</script>

<style scoped lang="scss">
.fullscreen-content {
  height: calc(var(--app-height));
}
</style>
