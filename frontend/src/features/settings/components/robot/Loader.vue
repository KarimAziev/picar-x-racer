<template>
  <FieldsetSkeleton :count="8"></FieldsetSkeleton>
</template>
<script setup lang="ts">
import FieldsetSkeleton from "@/ui/FieldsetSkeleton.vue";
defineProps<{ idPrefix?: string }>();
</script>
