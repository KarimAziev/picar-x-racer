<template>
  <div class="p-field" :class="fieldClassName">
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
export type Props = {
  message?: string;
  label?: string;
  fieldClassName?: string;
  labelClassName?: string;
};
defineProps<Props>();
</script>
<style scoped lang="scss">
.label {
  font-weight: bold;
  position: relative;
  display: flex;
  flex-direction: column;
  .message {
    background-color: transparent;
    color: var(--red-400);
  }
}
@import "./field.scss";
:deep(.p-select-dropdown) {
  width: 0.8rem;

  .p-icon {
    position: relative;
    width: 0.5rem;
    right: 50%;
  }
}

:deep(.p-select-label) {
  padding: 0.15rem 0.4rem;

  @media (min-width: 576px) {
    padding: 0.25rem 0.7rem;
  }

  @media (min-width: 768px) {
    padding: 0.3rem 0.7rem;
  }

  @media (min-width: 1200px) {
    padding: 0.4rem 0.7rem;
  }
}
</style>
