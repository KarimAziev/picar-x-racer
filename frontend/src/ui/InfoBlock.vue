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
  flex-direction: column;
  padding: 1rem;
  width: 200px;
}

@media (min-width: 880px) {
  .info {
    width: 350px;
  }
}
</style>
