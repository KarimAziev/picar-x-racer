<template>
  <div v-if="loading"><ProgressSpinner /></div>
  <Fieldset
    v-else
    v-for="(group, groupName) in store.config"
    :key="groupName"
    toggleable
    collapsed
    :legend="startCase(groupName)"
  >
    <div class="flex gap-2">
      <div class="flex-1 min-w-0">
        <template
          v-if="group"
          v-for="(field, fieldName) in group"
          :key="fieldName"
        >
          <template v-if="!calibrationFieldNames[fieldName]">
            <SelectField
              :filter="false"
              :autoFilterFocus="false"
              simpleOptions
              v-if="field.options"
              :field="fieldName"
              :label="field?.label"
              :tooltip="field.description"
              v-model="store.data[groupName][fieldName]"
              :options="field.options"
            />
            <TextField
              fluid
              v-else-if="field.type === 'str'"
              :field="fieldName"
              :label="field?.label"
              :tooltip="field.description"
              v-model="store.data[groupName][fieldName]"
            />
            <RadioField
              v-if="Array.isArray(field.type)"
              :options="
                field.type.map((v) => ({
                  value: v,
                  label: labels[v as string],
                }))
              "
              :field="fieldName"
              :label="field?.label"
              :tooltip="field.description"
              v-model="store.data[groupName][fieldName]"
            />
          </template>
        </template>
      </div>
      <div class="flex-1 min-w-0">
        <div v-if="group" v-for="(field, fieldName) in group" :key="fieldName">
          <NumberInputField
            v-if="
              !calibrationFieldNames[fieldName] &&
              ['int', 'float'].includes(field.type)
            "
            :field="fieldName"
            :step="field.type === 'float' ? 0.1 : 1"
            :label="field?.label"
            :tooltip="field.description"
            v-model="store.data[groupName][fieldName]"
          />
        </div>
      </div>
    </div>
  </Fieldset>
  <div class="flex gap-2 justify-self-start mt-2">
    <Button
      @click="handleConfirm($event)"
      size="small"
      severity="danger"
      label="Save"
      class="w-fit"
    />
  </div>
  <ConfirmPopup group="hardware"
    ><template #message="slotProps">
      <div
        class="max-w-96 flex flex-col items-center w-full gap-4 border-b border-surface-200 dark:border-surface-700 p-4 mb-4 pb-0"
      >
        <i
          :class="slotProps.message.icon"
          class="text-6xl text-primary-500"
        ></i>
        <p>{{ slotProps.message.message }}</p>
        <p>
          If calibration is active, any unsaved calibration changes will also be
          saved along with the hardware configuration.
        </p>
      </div>
    </template>
  </ConfirmPopup>
</template>

<script setup lang="ts">
import { useRobotStore } from "@/features/settings/stores";
import ProgressSpinner from "primevue/progressspinner";
import SelectField from "@/ui/SelectField.vue";
import TextField from "@/ui/TextField.vue";
import NumberInputField from "@/ui/NumberInputField.vue";
import { onMounted, ref } from "vue";
import Fieldset from "primevue/fieldset";
import { startCase } from "@/util/str";
import { useConfirm } from "primevue/useconfirm";

import RadioField from "@/ui/RadioField.vue";
import { useControllerStore } from "@/features/controller/store";

const controllerStore = useControllerStore();
const store = useRobotStore();
const confirmDialog = useConfirm();
const calibrationFieldNames: { [key: string]: boolean } = {
  calibration_offset: true,
  calibration_direction: true,
};

const labels: { [key: string]: string } = {
  int: "PIN Number",
  str: "Name of the PIN",
};

const handleConfirm = (event: MouseEvent) => {
  confirmDialog.require({
    group: "hardware",
    target: event.currentTarget as HTMLElement,
    icon: "pi pi-power-off",
    modal: true,
    blockScroll: true,
    message: "Are you sure you want to save the hardware settings?",
    acceptProps: {
      severity: "danger",
      label: "Save",
    },
    accept: () => controllerStore.saveRobotConfig(store.data),
    rejectProps: {
      icon: "pi pi-times",
      label: "Cancel",
      outlined: true,
    },
  });
};

const loading = ref(true);

onMounted(async () => {
  loading.value = true;
  await store.fetchFieldsConfig();
  loading.value = false;
});
</script>
