<template>
  <div class="flex justify-between items-center select-none" :class="class">
    <span class="flex-1 font-bold">{{ label }}&nbsp;&nbsp;&nbsp;&nbsp;</span>
    <span class="text-right">{{ value }}{{ valueSuffix }}</span>
    <slot></slot>
  </div>
</template>
<script setup lang="ts">
defineProps<{
  label?: string;
  value?: string | number | null;
  valueSuffix?: string;
  class?: string;
}>();
</script>
