<template>
  <Fieldset v-if="enabledMotors.length" legend="Motors direction" toggleable>
    <div class="flex flex-col gap-y-2">
      <MotorDirection
        v-for="entry in enabledMotors"
        :key="entry.configIndex"
        layout="row"
        label-class-name="flex-1"
        @update:model-value="updateDirection(entry.serviceIndex, $event)"
        :label="entry.motor.name || `Motor ${entry.configIndex + 1}`"
        v-model="entry.motor.calibration_direction"
      />
    </div>
  </Fieldset>
</template>

<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import { useRobotStore } from "@/features/settings/stores";
import Fieldset from "primevue/fieldset";
import MotorDirection from "@/features/settings/components/calibration/MotorDirection.vue";
import { computed } from "vue";

const controllerStore = useControllerStore();
const robotStore = useRobotStore();

const enabledMotors = computed(() =>
  robotStore.data.motors
    .flatMap((motor, configIndex) =>
      motor.enabled ? [{ motor, configIndex }] : [],
    )
    .map((entry, serviceIndex) => ({ ...entry, serviceIndex })),
);

const updateDirection = (index: number, value: number) => {
  controllerStore.updateMotorCaliDir(index, value);
};
</script>
