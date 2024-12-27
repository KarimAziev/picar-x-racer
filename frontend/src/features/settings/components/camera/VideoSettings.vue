<template>
  <VideoDeviceSelect />
  <VideoQualitySelect
    v-tooltip="'Quality compression level for frames (0–100)'"
  />
  <VideoEnhancerSelect
    v-tooltip="
      'Video effect to apply to frames (e.g., `simulate_predator_vision`)'
    "
  />
</template>

<script setup lang="ts">
import VideoDeviceSelect from "@/features/settings/components/camera/VideoDeviceSelect.vue";
import VideoEnhancerSelect from "@/features/settings/components/camera/VideoEnhancerSelect.vue";
import VideoQualitySelect from "@/features/settings/components/camera/VideoQualitySelect.vue";
</script>
