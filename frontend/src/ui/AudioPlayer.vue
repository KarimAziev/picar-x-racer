<template>
  <div class="flex flex-col items-center">
    <ButtonIcon
      @click="playing = !playing"
      aria-label="toggle-play"
      :icon="togglePlayIcon"
      class="py-2 px-2 hover:bg-button-text-primary-hover-background disabled:hover:bg-transparent disabled:opacity-60"
      v-tooltip="'Toggle playing'"
    ></ButtonIcon>
    <span class="whitespace-nowrap text-[8px]">
      {{ durationLabel }}
    </span>

    <audio ref="audioFile" :src="src" preload="none" />
  </div>
</template>

<script setup lang="ts">
import { useTemplateRef, computed } from "vue";
import { useMediaControls } from "@/features/detection/composables/useMediaControls";
import ButtonIcon from "@/ui/ButtonIcon.vue";
import { isNumber } from "@/util/guards";
import { secondsToReadableString } from "@/util/time";

const props = defineProps<{ src: string }>();

const audioFile = useTemplateRef("audioFile");
const { playing, currentTime, duration } = useMediaControls(audioFile, {
  src: props.src,
});

const togglePlayIcon = computed(
  () => `pi ${playing.value ? "pi-pause" : "pi-play"}`,
);

const durationLabel = computed(() =>
  duration.value !== 0 &&
  isNumber(duration.value) &&
  isNumber(currentTime.value)
    ? [
        secondsToReadableString(currentTime.value),
        secondsToReadableString(duration.value),
      ].join(" / ")
    : "",
);
</script>
