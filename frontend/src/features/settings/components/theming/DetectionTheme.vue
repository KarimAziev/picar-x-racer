<template>
  <Fieldset toggleable legend="Detection Theme">
    <div>
      <Fieldset toggleable legend="Label and Bounding Box Color">
        <DetectionBoxes />
      </Fieldset>
      <Fieldset toggleable legend="Pose Estimation">
        <PoseLines />
        <div class="flex flex-wrap items-center">
          <div class="font-medium">Keypoints:</div>
          <Keypoints />
        </div>
      </Fieldset>
    </div>

    <DetectionPreview />
  </Fieldset>
</template>

<script setup lang="ts">
import Fieldset from "primevue/fieldset";
import DetectionPreview from "@/features/settings/components/theming/DetectionPreview.vue";
import DetectionBoxes from "@/features/settings/components/theming/DetectionBoxes.vue";
import PoseLines from "@/features/settings/components/theming/PoseLines.vue";
import Keypoints from "@/features/settings/components/theming/Keypoints.vue";
</script>
