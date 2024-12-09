<template>
  <div class="flex">
    <NumberField
      fieldClassName="opacity-hover"
      @keydown.stop="doNothing"
      @keyup.stop="doNothing"
      :step="5"
      :min="0"
      :max="100"
      @keypress.stop="doNothing"
      @update:model-value="handleUpdateVolume"
      v-model="currVolume"
      field="volume"
      label="Volume"
    />

    <Field label="Audio stream" :fieldClassName="fieldStreamClass">
      <Button
        class="stream-btn"
        size="small"
        :icon="iconName"
        text
        aria-label="audio-stream"
        v-tooltip="'Turn on audio stream'"
        @click="musicStore.toggleStreaming"
        :disabled="loading"
      >
      </Button>
    </Field>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted, watch, computed } from "vue";
import { useWebsocketAudio } from "@/composables/useAudioStream";
import Button from "primevue/button";
import { useMusicStore } from "@/features/music";
import NumberField from "@/ui/NumberField.vue";
import { useAsyncDebounce } from "@/composables/useDebounce";
import Field from "@/ui/Field.vue";

const musicStore = useMusicStore();

const currVolume = ref(musicStore.volume);

const fieldStreamClass = computed(
  () => `${connected.value ? "" : "opacity-hover"}`,
);

const handleUpdateVolume = useAsyncDebounce(async (value: number) => {
  if (musicStore.volume !== value) {
    await musicStore.setVolume(value);
  }
}, 500);

const { startAudio, stopAudio, connected, loading, cleanup } =
  useWebsocketAudio("ws/audio-stream");

const doNothing = () => {};

const iconName = computed(
  () => `pi ${connected.value ? "pi-volume-up" : "pi-volume-off"}`,
);

watch(
  () => musicStore.isStreaming,
  (newVal) => {
    if (newVal && !connected.value && !loading.value) {
      startAudio();
    } else {
      stopAudio();
    }
  },
);

const handleSocketsCleanup = () => {
  window.removeEventListener("beforeunload", handleSocketsCleanup);
  cleanup();
};

watch(
  () => musicStore.volume,
  (newVal) => {
    currVolume.value = newVal;
  },
);

onMounted(() => {
  window.addEventListener("beforeunload", handleSocketsCleanup);
  if (musicStore.isStreaming) {
    startAudio();
  }
});

onBeforeUnmount(() => {
  handleSocketsCleanup();
});
</script>
<style scoped lang="scss">
.stream-btn {
  align-self: normal;
  padding: 0;
}
:deep(.p-inputtext) {
  width: 70px;
}
</style>
