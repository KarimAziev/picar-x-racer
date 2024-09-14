<template>
  <label :class="labelClassName" :for="fieldName"
    >{{ label }}
    <span v-if="message" class="message">
      {{ message }}
    </span>
  </label>
</template>

<script setup lang="ts">
export type Props = {
  message?: string;
  label?: string;
  fieldName?: string;
  labelClassName?: string;
};

defineProps<Props>();
</script>
<style scoped lang="scss">
label {
  font-weight: bold;
  position: relative;
  display: flex;
  flex-direction: column;
}
.message {
  background-color: transparent;
  font-size: 12px;
  color: var(--red-400);
}
</style>
