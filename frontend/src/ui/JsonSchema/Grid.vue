<template>
  <div
    class="w-full min-w-0 [&>*]:min-w-0 [&>*]:max-w-full"
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

<style scoped>
:deep(.p-inputtext:not(.p-select-filter)),
:deep(.p-treeselect),
:deep(.p-select),
:deep(.p-cascadeselect),
:deep(.p-inputnumber),
:deep(.tree-btn),
:deep(.select-root),
:deep(.p-datepicker-input),
:deep(.p-multiselect) {
  min-width: 0;
  max-width: 100%;
}

:deep(.p-inputnumber-input) {
  min-width: 0;
  width: 100%;
}
</style>
