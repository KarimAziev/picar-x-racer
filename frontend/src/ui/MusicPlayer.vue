<template>
  <div class="player">
    <div>
      <div class="title">{{ song }}</div>
      <Slider
        @update:model-value="debounceHandleStartUpdate"
        :disabled="disabled"
        v-model="musicStore.start"
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
        @click="pauseTrack"
        icon="pi pi-pause"
        text
        :disabled="disabled"
        aria-label="Pause"
        v-tooltip="'Pause playing track'"
      />
      <Button
        @click="playCurrentTrack"
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
import { useMusicStore, useSettingsStore } from "@/features/settings/stores";
import { isNumber } from "@/util/guards";
import { secondsToReadableString } from "@/util/time";
import { useAsyncDebounce } from "@/composables/useDebounce";

const musicStore = useMusicStore();
const settingsStore = useSettingsStore();

const debounceHandleStartUpdate = useAsyncDebounce(async () => {
  if (musicStore.playing) {
    await musicStore.resumeMusic();
  }
}, 1000);

const nextTrack = async () => {
  await musicStore.nextTrack();
};
const song = computed(
  () => musicStore.track || settingsStore.settings.default_music,
);

const disabled = computed(() => musicStore.trackLoading);

const duration = computed(() => musicStore.duration);

const durationLabel = computed(() =>
  isNumber(musicStore.duration) && isNumber(musicStore.start)
    ? [
        secondsToReadableString(musicStore.start),
        secondsToReadableString(musicStore.duration),
      ].join(" / ")
    : "00:00 / 00:00",
);

const playCurrentTrack = () => {
  if (musicStore.track) {
    musicStore.resumeMusic();
  } else {
    musicStore.playMusic(settingsStore.settings.default_music || null);
  }
};

const prevTrack = () => {
  musicStore.prevTrack();
};

const pauseTrack = () => {
  musicStore.pauseMusic();
};

const stopTrack = async () => {
  await musicStore.stopMusic();
};

const isPlaying = computed(() => musicStore.playing);
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
}

.title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.p-slider) {
  .p-slider-handle {
    transform: scale(0.5);
  }
}
</style>
