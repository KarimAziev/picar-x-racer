<template>
  <div :class="class" class="flex items-center text-inherit">
    <span class="bold">{{ value }}V</span>
    <i class="pi pi-bolt"></i>
    <span class="bold">{{ percentage }}%</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ class?: string; value: number; percentage: number }>();
</script>
