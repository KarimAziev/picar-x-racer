<template>
  <div :class="class">
    {{ label }}
    <span>{{ percentage }}%</span>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  class?: string;
  percentage: number | string;
  label?: string;
}>();
</script>
