<template>
  <div class="absolute right-[1px] z-12" :class="class"><slot></slot></div>
</template>

<script setup lang="ts">
defineProps<{ class?: string }>();
</script>
