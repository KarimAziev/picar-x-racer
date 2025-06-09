<template>
  <Fieldset legend="General" toggleable collapsed :id="popupStore.tab">
    <RobotSettings />
    <Divider />
    <Button
      size="small"
      outlined
      severity="warning"
      label="Save"
      @click="
        settingsStore.saveData({
          robot: settingsStore.data.robot,
        })
      "
      class="w-fit mt-4"
    />
  </Fieldset>
  <CalibrationPanel :id="`${popupStore.tab}-1`" />
  <RobotConfig :idPrefix="`${popupStore.tab}-2`" />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import ErrorComponent from "@/ui/ErrorComponent.vue";
import { useSettingsStore, usePopupStore } from "@/features/settings/stores";
import RobotConfigLoader from "@/features/settings/components/robot/Loader.vue";
import FieldsetSkeleton from "@/ui/FieldsetSkeleton.vue";
import Fieldset from "@/ui/Fieldset.vue";

const settingsStore = useSettingsStore();
const popupStore = usePopupStore();

const RobotConfig = defineAsyncComponent({
  loader: () => import("@/features/settings/components/robot/RobotConfig.vue"),
  loadingComponent: RobotConfigLoader,
  delay: 0,
});

const RobotSettings = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/robot/RobotSettings.vue"),
  loadingComponent: FieldsetSkeleton,
  delay: 0,
  errorComponent: ErrorComponent,
});
const CalibrationPanel = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/calibration/CalibrationPanel.vue"),
  loadingComponent: FieldsetSkeleton,
  delay: 0,
});
</script>
