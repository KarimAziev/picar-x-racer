<template>
  <div class="top-right-panel" :class="class"><slot></slot></div>
</template>

<script setup lang="ts">
defineProps<{ class?: string }>();
</script>

<style scoped lang="scss">
.top-right-panel {
  position: absolute;
  right: 1px;
  z-index: 12;
}
</style>
