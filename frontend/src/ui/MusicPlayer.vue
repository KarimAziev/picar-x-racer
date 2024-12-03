<template>
  <div class="player">
    <div>
      <div class="title">{{ currentTrack }}</div>
      <Slider
        @change="handlePositionUpdate"
        :disabled="disabled"
        v-model="musicStore.player.position"
        :max="duration"
        v-if="duration"
      />
    </div>

    <div class="buttons">
      <Button
        @click="prevTrack"
        icon="pi pi-backward"
        aria-label="Prev track"
        text
        :disabled="disabled"
        v-tooltip="'Previous track'"
      />

      <Button
        v-if="isPlaying"
        @click="togglePlaying"
        icon="pi pi-pause"
        text
        :disabled="disabled"
        aria-label="Pause"
        v-tooltip="'Pause playing track'"
      />
      <Button
        @click="togglePlaying"
        v-else
        icon="pi pi-play-circle"
        text
        aria-label="Play"
        :disabled="disabled"
        v-tooltip="'Play track'"
      />
      <Button
        @click="stopTrack"
        icon="pi pi-stop"
        :disabled="disabled || !isPlaying"
        text
        aria-label="Stop"
        v-tooltip="'Stop playing'"
      />
      {{ durationLabel }}

      <Button
        @click="nextTrack"
        :disabled="disabled"
        icon="pi pi-forward"
        aria-label="Next track"
        v-tooltip="'Play next track'"
        text
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import Slider from "primevue/slider";
import { useMusicStore } from "@/features/settings/stores";
import { isNumber } from "@/util/guards";
import { secondsToReadableString } from "@/util/time";
import { useAsyncDebounce } from "@/composables/useDebounce";

const musicStore = useMusicStore();

const currentTrack = computed(() => musicStore.player.track);
const isPlaying = computed(() => musicStore.player.is_playing);
const disabled = computed(() => musicStore.trackLoading);

const duration = computed(() => musicStore.player.duration);

const durationLabel = computed(() =>
  isNumber(musicStore.player.duration) && isNumber(musicStore.player.position)
    ? [
        secondsToReadableString(musicStore.player.position),
        secondsToReadableString(musicStore.player.duration),
      ].join(" / ")
    : "00:00 / 00:00",
);

const handlePositionUpdate = useAsyncDebounce(async (value: number) => {
  await musicStore.updatePosition(value);
}, 50);

const togglePlaying = async () => {
  await musicStore.togglePlaying();
};
const nextTrack = async () => {
  await musicStore.nextTrack();
};

const prevTrack = async () => {
  await musicStore.prevTrack();
};

const stopTrack = async () => {
  await musicStore.stopPlaying();
};
</script>

<style scoped lang="scss">
.player {
  display: flex;
  flex-direction: column;
  padding-left: 1rem;
  position: relative;
  font-size: 0.8rem;
  width: 300px;
  user-select: none;
}
.buttons {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
}

.title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.p-button) {
  padding-top: 0;
}

:deep(.p-slider) {
  cursor: pointer;
  .p-slider-handle {
    transform: scale(0.6);
  }
}
</style>
