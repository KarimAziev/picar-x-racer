<template>
  <div class="fields">
    <div v-for="(_value, field) in store.data" :key="field" class="field">
      <label :for="`${field}`">{{ field }}</label>
      <InputText
        class="text-input"
        size="small"
        :id="field"
        v-model="store.data[field]"
        disabled
      />
    </div>
    <div class="field">
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
import InputText from "primevue/inputtext";

const store = useCalibrationStore();
const controllerStore = useControllerStore();
</script>

<style scoped lang="scss">
.fields {
  margin: auto;
  justify-content: center;
  align-items: center;
  flex-direction: column;
}

.field {
  display: flex;
  gap: 10px;
  margin: 10px 0;
  button {
    white-space: nowrap;
    max-width: 150px;
  }
  .text-input {
    width: 50%;
  }
  label {
    width: 50%;
  }
}
</style>
