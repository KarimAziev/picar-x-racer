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
import { defineAsyncComponent } from "vue";
import DetectionBoxes from "@/features/settings/components/theming/DetectionBoxes.vue";
import PoseLinesSettings from "@/features/settings/components/theming/PoseLinesSettings.vue";
import KeypointsSettings from "@/features/settings/components/theming/KeypointsSettings.vue";
import ErrorComponent from "@/ui/ErrorComponent.vue";
import Skeleton from "@/ui/Skeleton.vue";

const DetectionPreview = defineAsyncComponent({
  loader: (): Promise<
    typeof import("@/features/settings/components/theming/DetectionPreview.vue")
  > =>
    new Promise((res) =>
      setTimeout(
        () =>
          import(
            "@/features/settings/components/theming/DetectionPreview.vue"
          ).then(res),
        100,
      ),
    ),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 200,
});
</script>
