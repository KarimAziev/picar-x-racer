<template>
  <Fieldset toggleable legend="Label and Bounding Box Color">
    <DetectionBoxes />
  </Fieldset>
  <Fieldset toggleable legend="Pose estimation">
    <PoseLinesSettings />
    <KeypointsSettings />
  </Fieldset>
  <DetectionPreview />
</template>

<script setup lang="ts">
import DetectionBoxes from "@/features/settings/components/theming/DetectionBoxes.vue";
import PoseLinesSettings from "@/features/settings/components/theming/PoseLinesSettings.vue";
import KeypointsSettings from "@/features/settings/components/theming/KeypointsSettings.vue";
import DetectionPreview from "@/features/settings/components/theming/DetectionPreview.vue";
</script>
