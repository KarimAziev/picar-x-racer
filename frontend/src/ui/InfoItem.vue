<template>
  <div class="info-item" :class="class">
    <span class="info-label">{{ label }}</span>
    <samp class="info-value">{{ value }}&nbsp;{{ valueSuffix }}</samp>
    <slot></slot>
  </div>
</template>
<script setup lang="ts">
defineProps<{
  label?: string;
  value?: string | number;
  valueSuffix?: string;
  class?: string;
}>();
</script>
<style scoped lang="scss">
.info-item {
  display: flex;
  color: var(--p-primary-200);
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-weight: bold;
  flex: 1;
}

.info-value {
  flex: 1;
  text-align: right;
}
</style>
