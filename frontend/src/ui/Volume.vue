<template>
  <div :class="class" class="flex items-center gap-1 text-sm">
    <div class="flex flex-col items-center justify-center">
      <ButtonIcon
        text
        @click="handleInc"
        class="py-0 px-2 hover:bg-button-text-primary-hover-background disabled:hover:bg-transparent disabled:opacity-60"
      >
        <i class="pi pi-angle-up" />
      </ButtonIcon>
      <div class="text-xs" v-tooltip="'System volume'">{{ currentValue }}</div>
      <ButtonIcon
        @click="handleDec"
        class="py-0 px-2 hover:bg-button-text-primary-hover-background disabled:hover:bg-transparent disabled:opacity-60"
      >
        <i class="pi pi-angle-down" />
      </ButtonIcon>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useMusicStore } from "@/features/music";
import { useAsyncDebounce } from "@/composables/useDebounce";
import ButtonIcon from "@/ui/ButtonIcon.vue";

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
