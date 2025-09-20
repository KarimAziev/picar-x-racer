<template>
  <Panel
    :pt="{
      header: () => ({
        class: ['pb-0! relative'],
      }),
    }"
  >
    <template #header>
      <div class="flex w-full justify-end absolute top-1 left-0">
        <Button
          @click="handleRemove"
          icon="pi pi-times"
          class="p-button-rounded p-button-danger p-button-text"
        />
      </div>
    </template>
    <slot></slot>
  </Panel>
</template>

<script setup lang="ts">
const emit = defineEmits(["remove:click"]);

const handleRemove = () => {
  emit("remove:click");
};
</script>
