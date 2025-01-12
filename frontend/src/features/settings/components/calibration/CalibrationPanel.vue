<template>
  <Fieldset legend="Calibration" toggleable :collapsed="collapsed">
    <slot></slot>
    <div class="flex flex-col gap-y-2">
      <Servos />
      <Motors />
      <div>
        <span class="flex gap-2 justify-self-start">
          <Button
            severity="danger"
            size="small"
            text
            @click="controllerStore.resetCalibration"
            >Reset</Button
          >
          <Button
            @click="controllerStore.toggleCalibration"
            size="small"
            outlined
            class="w-fit"
            >{{
              controllerStore.calibrationMode
                ? "Stop calibration"
                : "Start calibration"
            }}</Button
          >
          <Button
            size="small"
            label="Save"
            @click="handleSaveClick"
            class="w-fit"
          />
        </span>
      </div>
    </div>
  </Fieldset>
</template>

<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import Servos from "@/features/settings/components/calibration/Servos.vue";
import Motors from "@/features/settings/components/calibration/Motors.vue";
import Fieldset from "primevue/fieldset";

const props = defineProps<{ handleSave?: Function; collapsed?: boolean }>();

const handleSaveClick = () => {
  if (props.handleSave) {
    props.handleSave();
  } else {
    controllerStore.saveCalibration();
  }
};

const controllerStore = useControllerStore();
</script>
