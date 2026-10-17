<template>
  <div class="schema-grid-container w-full min-w-0">
    <div
      class="schema-grid grid gap-x-4 gap-y-3 [&>*]:min-w-0 [&>*]:max-w-full"
      :class="{ 'items-end': alignEnd }"
    >
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ alignEnd?: boolean }>();
</script>

<style scoped>
.schema-grid-container {
  container-type: inline-size;
}

.schema-grid {
  grid-template-columns: minmax(0, 1fr);
}

@container (min-width: 40rem) {
  .schema-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

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
