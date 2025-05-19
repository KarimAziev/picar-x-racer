<template>
  <div class="flex gap-2">
    <div class="flex-1 min-w-0 flex flex-col gap-2">
      <VideoFormatSelect />
      <VideoQualitySelect />
      <VideoRotationSelect />
    </div>
    <div class="flex-1 min-w-0 flex flex-col gap-2">
      <VideoEnhancerSelect />
      <AutoStopCameraToggle />
    </div>
  </div>
</template>

<script setup lang="ts">
import VideoEnhancerSelect from "@/features/settings/components/camera/VideoEnhancerSelect.vue";
import VideoQualitySelect from "@/features/settings/components/camera/VideoQualitySelect.vue";
import VideoFormatSelect from "@/features/settings/components/camera/VideoFormatSelect.vue";
import AutoStopCameraToggle from "@/features/settings/components/camera/AutoStopCameraToggle.vue";
import VideoRotationSelect from "@/features/settings/components/camera/VideoRotationSelect.vue";
</script>
