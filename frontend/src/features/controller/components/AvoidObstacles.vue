<template>
  <div class="flex justify-between items-center">
    <span class="font-bold">AVOID OBSTACLES</span>
    <ButtonIcon
      v-tooltip.left="
        active ? 'Deactivate avoid obstacles' : 'Activate avoid obstacles'
      "
      @click="handleToggle"
      class="cursor-pointer px-2 py-0 border border-current rounded-md bg-transparent transition-opacity duration-300 ease-in-out hover:bg-button-text-primary-hover-background focus:opacity-70 focus:outline-none focus:ring-2 focus:ring-current"
    >
      {{ label }}
    </ButtonIcon>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";
import ButtonIcon from "@/ui/ButtonIcon.vue";

const controllerStore = useControllerStore();

const handleToggle = () => {
  controllerStore.toggleAvoidObstaclesMode();
};
const active = computed(() => controllerStore.avoidObstacles);
const label = computed(() => (active.value ? "ON" : "OFF"));
</script>
