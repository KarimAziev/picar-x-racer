<template>
  <div class="flex gap-2">
    <div class="flex-1 min-w-0">
      <VideoQualitySelect />
    </div>
    <div class="flex-1 min-w-0">
      <VideoEnhancerSelect />
    </div>
  </div>
</template>

<script setup lang="ts">
import VideoEnhancerSelect from "@/features/settings/components/camera/VideoEnhancerSelect.vue";
import VideoQualitySelect from "@/features/settings/components/camera/VideoQualitySelect.vue";
</script>
