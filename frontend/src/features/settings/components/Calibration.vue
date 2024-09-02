<template>
  <Panel>
    <div class="fields">
      <div v-for="(_value, field) in store.data" :key="field" class="field">
        <label :for="`${field}`">{{ field }}</label>
        <InputText :id="field" v-model="store.data[field]" disabled />
      </div>
    </div>
  </Panel>
</template>

<script setup lang="ts">
import { useCalibrationStore } from "@/features/settings/stores";
import InputText from "primevue/inputtext";
import Panel from "primevue/panel";

const store = useCalibrationStore();
</script>

<style scoped lang="scss">
.fields {
  display: flex;
  flex-direction: column;
}
.field {
  display: flex;
  gap: 10px;
  margin: 10px 0;
  label {
    width: 50%;
  }
}
</style>
