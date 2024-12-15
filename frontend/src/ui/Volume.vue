<template>
  <div
    :class="class"
    class="flex align-items-center wrapper gap-2"
    v-tooltip="'System volume'"
  >
    <div class="flex flex-col jc-center align-items-center">
      <Button text @click="handleInc" size="small" icon="pi pi-angle-up" />
      {{ currentValue }}%
      <Button text @click="handleDec" size="small" icon="pi pi-angle-down" />
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
<style scoped lang="scss">
.wrapper {
  font-size: 0.8rem;
}
button {
  padding: 0px;
  height: unset;
  margin: 0;
  width: unset;
}

$adjust-btn-pos: 8px;

button:first-child {
  position: relative;
  top: $adjust-btn-pos;
}
button:last-child {
  bottom: $adjust-btn-pos;
}
</style>
