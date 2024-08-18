<template>
  <ProgressSpinner v-if="loading" />
  <slot v-else></slot>
</template>
<script setup lang="ts">
defineProps<{ loading?: boolean }>();
</script>
<style scoped lang="scss"></style>
