<template>
  <Fieldset legend="Motors direction" toggleable>
    <div class="flex flex-col gap-y-2">
      <div
        v-for="(obj, groupName) in motorHandlers"
        class="flex justify-between items-center select-none"
        :key="groupName"
        v-if="robotStore.data"
      >
        <span class="flex-1 font-bold">
          {{ startCase(groupName) }}: &nbsp;
          {{ robotStore.data[groupName]?.calibration_direction }}
        </span>
        <Button size="small" @click="obj.calibration_direction" outlined>
          Reverse
        </Button>
      </div>
    </div>
  </Fieldset>
</template>

<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import { useRobotStore } from "@/features/settings/stores";
import { startCase } from "@/util/str";
import type { MotorsCalibrationData } from "@/features/settings/stores/robot";
import type { MapObjectsDeepTo } from "@/util/ts-helpers";
import Fieldset from "primevue/fieldset";

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
