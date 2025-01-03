<template>
  <div :class="class" class="flex items-center gap-1 text-sm">
    <div class="flex flex-col items-center justify-center">
      <button
        text
        @click="handleInc"
        class="relative top-1 p-0 h-auto m-0 w-auto hover:text-primary-300"
      >
        <i class="pi pi-angle-up" />
      </button>
      <div v-tooltip="'System volume'">{{ currentValue }}</div>
      <button
        @click="handleDec"
        class="relative p-0 h-auto m-0 w-auto hover:text-primary-300"
      >
        <i class="pi pi-angle-down" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useMusicStore } from "@/features/music";
import { useAsyncDebounce } from "@/composables/useDebounce";

const musicStore = useMusicStore();
const currentValue = ref(musicStore.volume || 0);

defineProps<{ class?: string }>();

const handleUpdateVolume = useAsyncDebounce(async (value: number) => {
  if (musicStore.volume !== value && value <= 100 && value >= 0) {
    await musicStore.setVolume(value);
  }
}, 500);

const handleInc = () => {
  currentValue.value = Math.min(100, currentValue.value + 5);
  handleUpdateVolume(currentValue.value);
};

const handleDec = () => {
  currentValue.value = Math.max(0, currentValue.value - 5);
  handleUpdateVolume(currentValue.value);
};

watch(
  () => musicStore.volume,
  (newVal) => {
    currentValue.value = newVal || 0;
  },
);
</script>
