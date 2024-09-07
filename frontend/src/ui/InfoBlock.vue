<template>
  <div class="info" :class="class">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
defineProps<{ class?: string }>();
</script>

<style scoped lang="scss">
.info {
  text-transform: uppercase;
  display: flex;
  width: 350px;
  flex-direction: column;
  padding: 1rem;
}
</style>
