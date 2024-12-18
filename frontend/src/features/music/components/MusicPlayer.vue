<template>
  <div class="wrapper flex align-items-end gap-2">
    <div class="player">
      <div>
        <div class="title">
          {{ currentTrack }}
        </div>
        <Slider
          v-model="musicStore.player.position"
          @slideend="handleSavePosition"
          @keyup.stop="handleSavePosition"
          @mouseup="handleSavePosition"
          @mousedown="handleModelValueUpdate"
          @keydown.stop="handleModelValueUpdate"
          @change="handleModelValueUpdate"
          @update:model-value="handleModelValueUpdate"
          :max="duration"
          v-if="duration"
        />
      </div>

      <div class="buttons flex align-items-center jc-between">
        <Button
          @click="prevTrack"
          icon="pi pi-backward"
          aria-label="Prev track"
          text
          v-tooltip="'Previous track'"
        />

        <Button
          v-if="isPlaying"
          @click="togglePlaying"
          icon="pi pi-pause"
          text
          aria-label="Pause"
          v-tooltip="'Pause playing track'"
        />
        <Button
          @click="togglePlaying"
          v-else
          icon="pi pi-play-circle"
          text
          aria-label="Play"
          v-tooltip="'Play track'"
        />
        <Button
          @click="stopTrack"
          icon="pi pi-stop"
          :disabled="!isPlaying"
          text
          aria-label="Stop"
          v-tooltip="'Stop playing'"
        />
        <span class="duration">
          {{ durationLabel }}
        </span>
        <Button
          @click="nextTrack"
          icon="pi pi-forward"
          aria-label="Next track"
          v-tooltip="'Play next track'"
          text
        />
        <Button
          v-if="musicMode === MusicMode.LOOP"
          @click="nextMode"
          icon="pi pi-sync"
          aria-label="loop"
          v-tooltip="'Play all tracks on repeat continuously.'"
          text
        />
        <Button
          v-if="musicMode === MusicMode.LOOP_ONE"
          @click="nextMode"
          icon="pi pi-arrow-right-arrow-left"
          aria-label="loop_one"
          v-tooltip="'Repeat the current track continuously.'"
          text
        />
        <Button
          v-if="musicMode === MusicMode.QUEUE"
          @click="nextMode"
          icon="pi pi-list"
          aria-label="queue"
          v-tooltip="'Play all tracks once in order, without repeating.'"
          text
        />
        <Button
          v-if="musicMode === MusicMode.SINGLE"
          @click="nextMode"
          icon="pi pi-stop-circle"
          aria-label="single"
          v-tooltip="'Play the current track once and stop playback.'"
          text
        />
      </div>
    </div>
    <Volume class="volume" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import Slider from "primevue/slider";
import { isNumber } from "@/util/guards";
import { secondsToReadableString } from "@/util/time";
import { useMusicStore, MusicMode } from "@/features/music";
import { useAsyncDebounce } from "@/composables/useDebounce";
import Volume from "@/ui/Volume.vue";

const musicStore = useMusicStore();

const currentTrack = computed(() => musicStore.player.track);
const isPlaying = computed(() => musicStore.player.is_playing);
const track = ref<string | null>();

const handleSavePosition = useAsyncDebounce(async (value: unknown) => {
  if (track.value && track.value !== currentTrack.value) {
    track.value = null;
    musicStore.inhibitPlayerSync = false;
    return;
  }

  if (isNumber(value)) {
    musicStore.player.position = value;
    await musicStore.updatePosition(value);
  } else {
    await musicStore.updatePosition(musicStore.player.position);
  }

  track.value = null;
  musicStore.inhibitPlayerSync = false;
}, 50);

const handleModelValueUpdate = async (value: number | number[]) => {
  track.value = musicStore.player.track;
  if (isNumber(value)) {
    musicStore.inhibitPlayerSync = true;
    musicStore.player.position = value;
    await handleSavePosition(value);
  }
};

const musicMode = computed(() => musicStore.player.mode);

const duration = computed(() => musicStore.player.duration);

const durationLabel = computed(() =>
  isNumber(musicStore.player.duration) && isNumber(musicStore.player.position)
    ? [
        secondsToReadableString(musicStore.player.position),
        secondsToReadableString(musicStore.player.duration),
      ].join(" / ")
    : "00:00 / 00:00",
);

const togglePlaying = async () => {
  await musicStore.togglePlaying();
};

const nextMode = async () => {
  await musicStore.nextMode();
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
.wrapper {
  position: relative;
}
.player {
  display: flex;
  flex-direction: column;
  position: relative;
  padding: 0 4px;
  font-size: 0.7rem;
  width: 180px;
  user-select: none;

  @media (min-width: 992px) and (orientation: portrait) {
    width: 200px;
  }

  @media (min-width: 992px) and (orientation: landscape) {
    width: 300px;
  }
}
.duration {
  white-space: nowrap;
}
.title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.p-button) {
  padding-top: 1px;
}

:deep(.p-slider) {
  cursor: pointer;
  .p-slider-handle {
    transform: scale(0.5);
  }
}
</style>
