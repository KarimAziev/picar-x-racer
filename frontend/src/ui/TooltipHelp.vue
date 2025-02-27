<template>
  <span
    class="relative hover:opacity-80 transition-opacity duration-200 ease-in-out after:content-['?'] after:text-[0.8rem] after:text-blue-500 after:relative after:-top-[5px] after:pointer-events-none cursor-pointer"
    v-tooltip="tooltip"
  ></span>
</template>

<script setup lang="ts">
defineProps<{ tooltip?: string }>();
</script>
