<template>
  <div class="flex relative" :class="classObject">
    <span class="font-bold" v-if="label" :class="labelClassName">
      {{ label }}
      <TooltipHelp v-if="tooltipHelp" :tooltip="tooltipHelp" />
    </span>
    <slot></slot>
    <span :class="messageClass" class="bg-transparent text-red-500 text-sm">
      {{ message }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import TooltipHelp from "@/ui/TooltipHelp.vue";

export type FieldLayout = "col" | "row-reverse" | "row" | "col-reverse";

export type Props = {
  message?: string | null;
  label?: string | null;
  fieldClassName?: string;
  labelClassName?: string;
  layout?: FieldLayout;
  tooltipHelp?: string;
  messageClass?: string;
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
