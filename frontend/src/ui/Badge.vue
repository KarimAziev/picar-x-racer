<template>
  <div class="text-inherit flex items-center" :class="class">
    <span> {{ value }}&nbsp;</span>
    <i class="pi text-inherit" :class="icon" />
  </div>
</template>

<script setup lang="ts">
defineProps<{ class?: string; value?: number | string; icon?: string }>();
</script>
