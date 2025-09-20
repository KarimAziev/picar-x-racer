<template>
  <Fieldset legend="Motors direction" toggleable>
    <div class="flex flex-col gap-y-2">
      <MotorDirection
        v-for="(obj, groupName) in motorHandlers"
        :key="groupName"
        v-if="robotStore.data"
        layout="row"
        label-class-name="flex-1"
        @update:model-value="obj.calibration_direction"
        :label="startCase(groupName)"
        v-model="robotStore.data[groupName].calibration_direction"
      />
    </div>
  </Fieldset>
</template>

<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import { useRobotStore } from "@/features/settings/stores";
import type { MotorsCalibrationData } from "@/features/settings/stores/robot";
import type { MapObjectsDeepTo } from "@/util/ts-helpers";
import Fieldset from "primevue/fieldset";
import MotorDirection from "@/features/settings/components/calibration/MotorDirection.vue";
import { startCase } from "@/util/str";

const controllerStore = useControllerStore();
const robotStore = useRobotStore();

const motorHandlers: MapObjectsDeepTo<MotorsCalibrationData, () => void> = {
  left_motor: {
    calibration_direction: controllerStore.reverseLeftMotor,
  },
  right_motor: {
    calibration_direction: controllerStore.reverseRightMotor,
  },
};
</script>
