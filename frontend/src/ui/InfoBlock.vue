<template>
  <div
    class="info uppercase flex flex-col w-full text-[0.8rem] max-w-[160px] md:text-[0.9rem] md:max-w-[210px] lg:text-[1rem] lg:max-w-[260px]"
    :class="class"
  >
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
defineProps<{ class?: string }>();
</script>
