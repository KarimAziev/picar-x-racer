<template>
  <div class="flex flex-col items-center justify-center mx-auto">
    <div
      v-for="(_value, field) in store.data"
      :key="field"
      class="flex gap-2 my-2 items-center w-full"
    >
      <label :for="`${field}`" class="w-1/2">{{ field }}</label>
      <InputNumber
        class="w-1/2"
        size="small"
        :inputId="field as string"
        v-model="store.data[field]"
        disabled
      />
    </div>
    <div class="flex justify-start gap-2 my-2 w-full">
      <Button @click="controllerStore.toggleCalibration">
        {{
          controllerStore.calibrationMode
            ? "Stop calibration"
            : "Start calibration"
        }}</Button
      >
      <Button @click="controllerStore.saveCalibration" outlined>
        Save calibration
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useCalibrationStore } from "@/features/settings/stores";
import { useControllerStore } from "@/features/controller/store";
import InputNumber from "primevue/inputnumber";

const store = useCalibrationStore();
const controllerStore = useControllerStore();
</script>
