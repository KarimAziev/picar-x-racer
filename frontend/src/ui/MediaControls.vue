<template>
  <Recording />
  <div class="wrapper flex flex-wrap align-items-center max-w-150">
    <ToggleableView setting="general.show_photo_capture_button">
      <PhotoButton />
    </ToggleableView>
    <ToggleableView setting="general.show_audio_stream_button">
      <AudioStream />
    </ToggleableView>
    <ToggleableView setting="general.show_video_record_button">
      <VideoRecordButton />
    </ToggleableView>
  </div>
</template>
<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import ToggleableView from "@/ui/ToggleableView.vue";

const Recording = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/camera/VideoRecordingIndicator.vue"),
});

const AudioStream = defineAsyncComponent({
  loader: () => import("@/ui/AudioStream.vue"),
});

const VideoRecordButton = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/camera/VideoRecordButton.vue"),
});

const PhotoButton = defineAsyncComponent({
  loader: () => import("@/ui/PhotoButton.vue"),
});
</script>
<style scoped lang="scss"></style>
