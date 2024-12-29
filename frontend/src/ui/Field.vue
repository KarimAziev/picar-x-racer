<template>
  <div class="p-field" :class="classObject">
    <span class="label" v-if="label" :class="labelClassName"
      >{{ label }}
      <span v-if="message" class="message">
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
};

const props = defineProps<Props>();

const classObject = computed(() => ({
  [props.layout ? props.layout : "col"]: true,
  [props.fieldClassName ? props.fieldClassName : ""]: !!props.fieldClassName,
}));
</script>
<style scoped lang="scss">
@use "./field.scss";
.label {
  font-weight: bold;
  position: relative;
  display: flex;
  flex-direction: column;
  .message {
    background-color: transparent;
    color: var(--color-red);
  }
}
</style>
