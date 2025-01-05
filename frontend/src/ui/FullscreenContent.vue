<template>
  <div
    class="h-[calc(var(--app-height))] flex flex-col items-center justify-center relative"
    :class="class"
  >
    <slot></slot>
  </div>
</template>
<script setup lang="ts">
defineProps<{ class?: string }>();
</script>
