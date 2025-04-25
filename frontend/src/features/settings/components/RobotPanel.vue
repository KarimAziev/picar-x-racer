<template>
  <Fieldset legend="General" toggleable collapsed :id="popupStore.tab">
    <Fieldset legend="Control" toggleable :id="`${popupStore.tab}-0`">
      <RobotSettings />
    </Fieldset>

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
      class="w-fit mt-2"
    />
  </Fieldset>
  <CalibrationPanel :id="`${popupStore.tab}-1`">
    <Message severity="warning" variant="simple" closable>
      Calibration will reset any unsaved changes in the Hardware Config section.
    </Message>
  </CalibrationPanel>
  <RobotConfig :idPrefix="`${popupStore.tab}-2`" />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import Skeleton from "@/features/settings/components/general/Skeleton.vue";
import ErrorComponent from "@/ui/ErrorComponent.vue";
import CalibrationPanel from "@/features/settings/components/calibration/CalibrationPanel.vue";
import { useSettingsStore, usePopupStore } from "@/features/settings/stores";
import Fieldset from "@/ui/Fieldset.vue";

const settingsStore = useSettingsStore();
const popupStore = usePopupStore();

const RobotConfig = defineAsyncComponent({
  loader: () => import("@/features/settings/components/robot/RobotConfig.vue"),
  loadingComponent: Skeleton,
  delay: 0,
});

const RobotSettings = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/robot/RobotSettings.vue"),
  loadingComponent: Skeleton,
  delay: 0,
  errorComponent: ErrorComponent,
});
</script>
