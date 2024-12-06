<template>
  <VideoDeviceSelect />
  <VideoQualitySelect />
  <VideoEnhancerSelect />
</template>

<script setup lang="ts">
import VideoDeviceSelect from "@/features/settings/components/camera/VideoDeviceSelect.vue";
import VideoEnhancerSelect from "@/features/settings/components/camera/VideoEnhancerSelect.vue";
import VideoQualitySelect from "@/features/settings/components/camera/VideoQualitySelect.vue";
</script>
