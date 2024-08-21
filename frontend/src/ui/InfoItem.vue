<template>
  <div class="info-item" :class="class">
    <samp class="info-label">{{ label }}</samp>
    <samp class="info-value">{{ value }}{{ valueSuffix }}</samp>
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
