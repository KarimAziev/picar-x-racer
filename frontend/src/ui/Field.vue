<template>
  <div class="flex relative" :class="classObject">
    <span class="flex flex-col font-bold" v-if="label" :class="labelClassName"
      >{{ label }}
      <span v-if="message" class="bg-transparent text-red-500 text-sm">
        {{ message }}
      </span>
    </span>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

export type FieldLayout = "col" | "row-reverse" | "row" | "col-reverse";

export type Props = {
  loading?: boolean;
  message?: string | null;
  label?: string;
  fieldClassName?: string;
  labelClassName?: string;
  layout?: FieldLayout;
  noMargin?: boolean;
};

const props = defineProps<Props>();

const extraProps: Partial<Record<FieldLayout, { [key: string]: boolean }>> = {
  row: {
    "gap-2.5": true,
    "items-center": true,
  },
};

const classObject = computed(() => {
  const layout = props.layout || "col";
  const extraLayotProps = extraProps[layout];
  return {
    [`flex-${layout}`]: true,
    ...extraLayotProps,
    [props.fieldClassName ? props.fieldClassName : ""]: !!props.fieldClassName,
  };
});
</script>
