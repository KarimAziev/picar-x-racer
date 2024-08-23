<template>
  <ProgressSpinner v-if="loading" />
  <slot v-else></slot>
</template>
<script setup lang="ts">
import ProgressSpinner from "primevue/progressspinner";

defineProps<{ loading?: boolean }>();
</script>
<style scoped lang="scss"></style>
