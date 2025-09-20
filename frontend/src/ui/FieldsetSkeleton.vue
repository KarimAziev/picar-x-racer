<template>
  <Fieldset
    class="relative"
    :collapsed="false"
    v-for="(_, i) in new Array(count).fill(1)"
    :key="i"
  >
    <template #legend>
      <div class="flex gap-2">
        <span
          class="font-['primeicons'] pi-plus text-fieldset-toggle-icon text-[14px]"
        />
        <Skeleton width="100px" />
      </div>
    </template>
  </Fieldset>
</template>
<script setup lang="ts">
withDefaults(
  defineProps<{ count?: number; idPrefix?: string; id?: string }>(),
  {
    count: 1,
  },
);
</script>
