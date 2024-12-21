<template>
  <div class="flex jc-between distance">
    <span class="bold">AVOID OBSTACLES</span>
    <button
      v-tooltip="'Click to toggle avoid obstacles mode'"
      @click="handleToggle"
      class="btn"
    >
      {{ label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";

const controllerStore = useControllerStore();

const handleToggle = () => {
  controllerStore.toggleAvoidObstaclesMode();
};

const label = computed(() => (controllerStore.avoidObstacles ? "ON" : "OFF"));
</script>

<style scoped lang="scss">
button {
  font-size: inherit;
  font-family: var(--font-family);
  cursor: pointer;
  padding: 0;
  color: var(--color-text);
  border: none;
  background-color: transparent;
  outline: none;
  transition: all 0.3s ease;
  &:hover {
    opacity: 0.7;
  }
}
</style>
