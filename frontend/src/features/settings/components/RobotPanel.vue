<template>
  <Fieldset legend="General" toggleable>
    <Fieldset legend="Control" toggleable>
      <RobotSettings />
    </Fieldset>

    <Fieldset legend="Battery" toggleable collapsed>
      <BatterySettings />
    </Fieldset>
    <Button
      size="small"
      outlined
      severity="warning"
      label="Save"
      @click="
        settingsStore.saveData({
          robot: settingsStore.data.robot,
          battery: settingsStore.data.battery,
        })
      "
      class="w-fit mt-2"
    />
  </Fieldset>
  <CalibrationPanel>
    <Message severity="warning" variant="simple" closable>
      Calibration will reset any unsaved changes in the Hardware Config section.
    </Message>
  </CalibrationPanel>
  <Fieldset legend="Hardware Config" toggleable collapsed>
    <RobotConfig />
  </Fieldset>
</template>

<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import Fieldset from "primevue/fieldset";
import Skeleton from "@/features/settings/components/general/Skeleton.vue";
import ErrorComponent from "@/ui/ErrorComponent.vue";
import CalibrationPanel from "@/features/settings/components/calibration/CalibrationPanel.vue";
import { useSettingsStore } from "@/features/settings/stores";

const settingsStore = useSettingsStore();

const BatterySettings = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/robot/BatterySettings.vue"),
  loadingComponent: Skeleton,
  delay: 0,
});

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
