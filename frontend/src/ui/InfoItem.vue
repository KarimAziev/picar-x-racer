<template>
  <div class="info-item" :class="class">
    <span class="info-label">{{ label }}&nbsp;&nbsp;&nbsp;&nbsp;</span>
    <span class="info-value">{{ value }}{{ valueSuffix }}</span>
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
  justify-content: space-between;
  align-items: center;
  user-select: none;
}

.info-label {
  font-weight: bold;
}

.info-value {
  text-align: right;
}
</style>
