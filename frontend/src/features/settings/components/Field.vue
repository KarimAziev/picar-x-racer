<template>
  <div class="field" :class="props.class">
    <label :class="props.labelClassName" :for="props.fieldName">{{
      props.label
    }}</label>
    <slot></slot>

    <div v-if="message" class="message">
      {{ message }}
    </div>
  </div>
</template>

<script setup lang="ts">
export type Props = {
  fieldName: string;
  class?: string;
  message?: string;
  label?: string;
  labelClassName?: string;
};

const props = defineProps<Props>();
</script>
<style scoped lang="scss">
.field {
  display: flex;
}
</style>
