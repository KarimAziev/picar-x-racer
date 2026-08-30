<template>
  <Panel
    :pt="{
      header: () => ({
        class: ['pb-0! relative'],
      }),
    }"
  >
    <template #header>
      <div class="flex w-full items-center justify-between top-1 left-0">
        <span class="text-md font-bold">{{ title }}</span>
        <Button
          @click="handleRemove"
          :disabled="removeDisabled"
          icon="pi pi-times"
          severity="danger"
          text
          rounded
          size="small"
          aria-label="Remove item"
        />
      </div>
    </template>
    <slot></slot>
  </Panel>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
  removeDisabled?: boolean;
}>();

const emit = defineEmits<{
  "remove:click": [];
}>();

const handleRemove = () => {
  emit("remove:click");
};
</script>
