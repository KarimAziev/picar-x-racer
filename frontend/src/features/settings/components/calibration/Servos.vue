<template>
  <Fieldset legend="Servos" toggleable>
    <div class="flex flex-col gap-y-2">
      <NumberInputField
        layout="row"
        v-for="(obj, groupName) in servoHandlers"
        :key="groupName"
        class="flex justify-between items-center select-none"
        :step="0.1"
        :min="0"
        :max="20"
        :label="startCase(`${groupName.replace(/_servo$/gm, '')}`)"
        v-model="robotStore.data[groupName].calibration_offset"
        @update:model-value="obj.calibration_offset"
        :useGrouping="false"
        :minFractionDigits="1"
        :maxFractionDigits="1"
        :allowEmpty="false"
      />
      <span class="flex gap-2 justify-self-start">
        <Button size="small" outlined @click="controllerStore.servoTest"
          >Test servos
        </Button>
      </span>
    </div>
  </Fieldset>
</template>

<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import { useRobotStore } from "@/features/settings/stores";
import { startCase } from "@/util/str";
import type { ServoCalibrationData } from "@/features/settings/stores/robot";
import { DeepObjectsToHandlers } from "@/util/ts-helpers";
import NumberInputField from "@/ui/NumberInputField.vue";
import Fieldset from "primevue/fieldset";

const controllerStore = useControllerStore();
const robotStore = useRobotStore();

const servoHandlers: DeepObjectsToHandlers<ServoCalibrationData, true> = {
  steering_servo: {
    calibration_offset: controllerStore.updateServoDirCali,
  },
  cam_pan_servo: {
    calibration_offset: controllerStore.updateCamPanCali,
  },
  cam_tilt_servo: {
    calibration_offset: controllerStore.updateCamTiltCali,
  },
};
</script>
