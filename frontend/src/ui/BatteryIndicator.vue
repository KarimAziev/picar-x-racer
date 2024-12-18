<template>
  <div :class="class" class="flex align-items-center">
    <span class="bold">{{ value }}V</span>
    <i class="pi pi-bolt"></i>
    <span class="bold">{{ percentage }}%</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ class?: string; value: number; percentage: number }>();
</script>
<style scoped lang="scss">
i {
  font-size: inherit;
}
</style>
