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
  width: fit-content;
  font-size: 0.8rem;

  @media (min-width: 992px) {
    font-size: 1rem;
    padding: 1rem;
  }
}
</style>
