<template>
  <div v-if="loading"><ProgressSpinner /></div>
  <JsonSchema
    v-else-if="store.config"
    v-for="(propSchema, propName) in store.config.properties"
    :level="0"
    :schema="propSchema"
    :model="store.data"
    :path="[propName]"
    :defs="store.config['$defs']"
    :idPrefix="`${idPrefix}-${propName}`"
  />
  <Teleport to="#settings-footer">
    <span class="flex gap-2 justify-self-start">
      <Button
        :disabled="loading"
        size="small"
        label="Save"
        type="submit"
        @click="handleConfirm($event)"
        class="w-fit"
      />
    </span>
  </Teleport>
  <ConfirmPopup group="hardware">
    <template #message="slotProps">
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
import { onMounted, ref } from "vue";
import ProgressSpinner from "primevue/progressspinner";
import { useConfirm } from "primevue/useconfirm";
import { useRobotStore } from "@/features/settings/stores";
import { useControllerStore } from "@/features/controller/store";
import JsonSchema from "@/ui/JsonSchema/JsonSchema.vue";

defineProps<{ idPrefix: string }>();

const controllerStore = useControllerStore();
const store = useRobotStore();
const confirmDialog = useConfirm();

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
