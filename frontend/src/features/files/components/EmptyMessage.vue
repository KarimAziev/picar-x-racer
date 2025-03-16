<template>
  <div class="text-center">
    {{ message }}
  </div>
</template>

<script setup lang="ts">
defineProps<{ message?: string }>();
</script>
