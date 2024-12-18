<template>
  <div class="badge flex align-items-center" :class="class">
    <span> {{ value }}&nbsp;</span>
    <i class="pi" :class="icon" />
  </div>
</template>

<script setup lang="ts">
defineProps<{ class?: string; value?: number | string; icon?: string }>();
</script>
<style scoped lang="scss">
i {
  font-size: inherit;
}
.badge {
  i {
    font-size: inherit;
  }
}
</style>
