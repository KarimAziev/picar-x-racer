<template>
  <div class="info-item">
    <span class="info-label">{{ label }}</span>
    <b class="info-value">{{ value }}°</b>
    <slot></slot>
  </div>
</template>
<script setup lang="ts">
defineProps<{ label?: string; value?: string | number }>();
</script>
<style scoped lang="scss">
.info-item {
  display: flex;
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
  min-width: 50px;
}
</style>
