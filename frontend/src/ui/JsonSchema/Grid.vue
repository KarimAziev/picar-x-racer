<template>
  <div
    :class="{
      'grid grid-cols-2 gap-2 justify-around': !inhibitGrid,
    }"
  >
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
defineProps<{ inhibitGrid: boolean }>();
</script>
