<template>
  <button
    class="cursor-pointer px-2 py-1 rounded-md bg-transparent hover:bg-button-text-primary-hover-background focus:opacity-70 focus:outline-none focus:ring-2 focus:ring-current"
    :class="class"
    v-bind="otherAttrs"
  >
    <template v-if="$slots.icon">
      <slot name="icon" :class="icon" />
    </template>
    <template v-else> <i :class="icon" /></template>
    <slot></slot>
  </button>
</template>

<script setup lang="ts">
import { useAttrs } from "vue";

defineProps<{ icon?: string; class?: string }>();

const otherAttrs = useAttrs();
</script>
