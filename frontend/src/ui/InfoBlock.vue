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
  width: 100%;
  font-size: 0.8rem;
  max-width: 160px;

  @media (min-width: 992px) {
    font-size: 0.9rem;
    max-width: 210px;
  }
  @media (min-width: 1200px) {
    font-size: 1rem;
    max-width: 260px;
  }
}
</style>
