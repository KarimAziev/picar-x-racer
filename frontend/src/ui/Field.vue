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
@import "./field.scss";
:deep(.p-select-dropdown),
:deep(.p-treeselect-dropdown) {
  width: 0.8rem;

  .p-icon {
    position: relative;
    width: 0.5rem;
    right: 50%;
  }
}
:deep(.p-inputtext),
:deep(.p-treeselect),
:deep(.p-select),
:deep(.p-inputnumber) {
  display: flex;
  align-items: center;
  max-width: 140px;
  height: 30px;

  @media (min-width: 576px) {
    height: 35px;
    max-width: 140px;
  }
  @media (min-width: 768px) {
    max-width: 190px;
  }

  @media (min-width: 992px) {
    max-width: 210px;
  }
  @media (min-width: 1200px) {
    height: 40px;
    max-width: 220px;
  }

  @media (min-width: 1440px) {
    max-width: 230px;
  }

  @media (min-width: 1600px) {
    max-width: 240px;
  }
}
</style>
