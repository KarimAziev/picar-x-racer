<template>
  <div
    class="flex min-h-[24rem] h-full flex-col items-center justify-center p-6 text-center text-surface-300"
  >
    <i :class="[icon, 'text-4xl']" aria-hidden="true"></i>
    <h2 class="mt-3 text-base font-semibold text-surface-100">{{ title }}</h2>
    <p class="mt-1 max-w-lg text-xs leading-relaxed text-surface-400">
      {{ description }}
    </p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon: string;
  title: string;
  description: string;
}>();
</script>
