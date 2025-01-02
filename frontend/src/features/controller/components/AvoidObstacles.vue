<template>
  <div class="flex justify-between items-center">
    <span class="font-bold">AVOID OBSTACLES</span>
    <button
      v-tooltip="'Click to toggle avoid obstacles mode'"
      @click="handleToggle"
      class="text-inherit font-inherit cursor-pointer px-0 py-0 text-current border-none bg-transparent outline-none transition-opacity duration-300 ease-in-out hover:opacity-70"
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
