<template>
  <div class="relative flex items-end gap-1">
    <div
      class="flex flex-col relative px-1 text-[0.7rem] w-[180px] select-none lg:w-[200px] xl:w-[300px]"
    >
      <div>
        <div class="whitespace-nowrap overflow-hidden text-ellipsis">
          {{ currentTrack }}
        </div>
        <Slider
          class="cursor-pointer"
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

      <div class="flex items-center justify-between">
        <button
          @click="prevTrack"
          class="py-2 px-2 hover:bg-button-text-primary-hover-background disabled:hover:bg-transparent disabled:opacity-60"
          aria-label="Prev track"
          text
          v-tooltip="'Previous track'"
        >
          <i class="pi pi-backward" />
        </button>
        <button
          @click="togglePlaying"
          aria-label="toggle-play"
          class="py-2 px-2 hover:bg-button-text-primary-hover-background disabled:hover:bg-transparent disabled:opacity-60"
          v-tooltip="'Toggle playing'"
        >
          <i :class="togglePlayIcon" />
        </button>
        <button
          class="py-2 px-2 hover:bg-button-text-primary-hover-background disabled:hover:bg-transparent disabled:opacity-60"
          @click="stopTrack"
          :disabled="!isPlaying"
          aria-label="Stop"
          v-tooltip="'Stop playing'"
        >
          <i class="pi pi-stop" />
        </button>
        <span class="whitespace-nowrap">
          {{ durationLabel }}
        </span>
        <button
          class="py-2 px-2 hover:bg-button-text-primary-hover-background disabled:hover:bg-transparent disabled:opacity-60"
          @click="nextTrack"
          aria-label="Next track"
          v-tooltip="'Play next track'"
        >
          <i class="pi pi-forward" />
        </button>
        <button
          class="py-2 px-2 hover:bg-button-text-primary-hover-background disabled:hover:bg-transparent disabled:opacity-60"
          @click="nextMode"
          aria-label="next-music-mode"
          v-tooltip="musicModeTooltip"
        >
          <i :class="musicModeIcon" />
        </button>
      </div>
    </div>
    <Volume />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import Slider from "primevue/slider";
import { isNumber } from "@/util/guards";
import { secondsToReadableString } from "@/util/time";
import { useMusicStore } from "@/features/music";
import { useAsyncDebounce } from "@/composables/useDebounce";
import Volume from "@/ui/Volume.vue";
import { musicModeConfig } from "@/features/music/components/config";

const musicStore = useMusicStore();

const currentTrack = computed(() => musicStore.player.track);
const isPlaying = computed(() => musicStore.player.is_playing);
const track = ref<string | null>();

const togglePlayIcon = computed(
  () => `pi ${musicStore.player.is_playing ? "pi-pause" : "pi-play-circle"}`,
);

const musicModeTooltip = computed(
  () => musicModeConfig[musicStore.player.mode]?.tooltip,
);

const musicModeIcon = computed(
  () => `pi ${musicModeConfig[musicStore.player.mode]?.icon}`,
);

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
