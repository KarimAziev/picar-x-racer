<template>
  <CalibrationPanel :id="id" v-if="calibrationMode" />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";
import CalibrationPanel from "@/features/settings/components/calibration/CalibrationPanel.vue";

defineProps<{ id: string }>();

const controllerStore = useControllerStore();

const calibrationMode = computed(() => controllerStore.calibrationMode);
</script>
