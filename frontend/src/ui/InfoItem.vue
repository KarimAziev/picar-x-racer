<template>
  <div class="flex justify-between items-center select-none" :class="class">
    <span class="flex-1 font-bold">
      <template v-if="$slots.label">
        <slot name="label" :label="label" />
      </template>
      <template v-else> {{ label }}&nbsp;&nbsp;&nbsp;&nbsp;</template>
    </span>
    <span class="text-right">
      <template v-if="$slots.value">
        <slot name="value" :value="value" />
      </template>
      <template v-else> {{ value }}{{ valueSuffix }} </template>
    </span>
    <slot></slot>
  </div>
</template>
<script setup lang="ts">
defineProps<{
  label?: string;
  value?: string | number | null;
  valueSuffix?: string;
  class?: string;
}>();
</script>
