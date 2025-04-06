<template>
  <button
    class="cursor-pointer rounded-md bg-transparent transition-opacity duration-300 ease-in-out hover:opacity-70 hover:bg-button-text-primary-hover-background focus:opacity-70 focus:outline-none focus:ring-current"
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
