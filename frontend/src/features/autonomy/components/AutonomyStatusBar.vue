<template>
  <header
    class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-surface-200 bg-surface-0/95 px-3 py-2 shadow-sm dark:border-surface-700 dark:bg-surface-900/95"
  >
    <div class="flex min-w-0 flex-wrap items-center gap-2">
      <Button
        aria-label="Return to camera driving view"
        icon="pi pi-home"
        severity="secondary"
        text
        rounded
        @click="router.push('/')"
      />
      <div class="mr-1 min-w-0">
        <div class="truncate text-sm font-semibold">Autonomy workspace</div>
        <div class="text-[0.68rem] text-surface-500 dark:text-surface-400">
          Manual mapping and runtime diagnostics
        </div>
      </div>
      <Tag :severity="modeSeverity" :value="modeLabel" />
      <Tag
        :severity="controlConnected ? 'success' : 'secondary'"
        :value="controlConnected ? 'Control connected' : 'Control offline'"
      />
      <Tag
        :severity="telemetry.connected ? 'success' : 'secondary'"
        :value="
          telemetry.connected ? 'Telemetry connected' : 'Telemetry offline'
        "
      />
      <Tag :severity="sensorSeverity" :value="sensorLabel" />
      <Tag
        v-if="telemetry.simulation"
        :severity="simulationSeverity"
        :value="simulationLabel"
      />
      <Tag
        v-if="telemetry.mappingSession"
        :severity="mappingSeverity"
        :value="`Map: ${telemetry.mappingSession.state}`"
      />
      <Tag severity="info" :value="commandLabel" />
      <Tag v-if="poseLabel" severity="secondary" :value="poseLabel" />
      <Tag
        v-if="controller.motionReason"
        :severity="controller.speed === 0 ? 'secondary' : 'warning'"
        :value="`Reason: ${controller.motionReason}`"
      />
      <Tag
        v-if="safetyLabel"
        :severity="safetyBlocked ? 'danger' : 'success'"
        :value="safetyLabel"
      />
    </div>

    <div class="flex flex-wrap items-center justify-end gap-2">
      <Button
        v-if="controller.robotMode !== 'manual'"
        label="Arm manual"
        icon="pi pi-play"
        size="small"
        :disabled="!canChangeNormalMode"
        @click="controller.setRobotMode('manual')"
      />
      <Button
        v-else
        label="Disarm"
        icon="pi pi-stop"
        severity="secondary"
        size="small"
        :disabled="!controlConnected"
        @click="disarm"
      />
      <Button
        v-if="controller.emergencyStopActive"
        label="Clear E-stop"
        icon="pi pi-unlock"
        severity="warning"
        size="small"
        :disabled="!controlConnected"
        @click="controller.clearEmergencyStop()"
      />
      <Button
        v-if="controller.motionFault"
        label="Clear fault"
        icon="pi pi-wrench"
        severity="warning"
        size="small"
        :disabled="!controlConnected"
        @click="controller.clearMotionFault()"
      />
      <Button
        label="E-stop"
        icon="pi pi-exclamation-triangle"
        severity="danger"
        size="small"
        :disabled="!controlConnected || controller.emergencyStopActive"
        @click="controller.emergencyStop('autonomy workspace operator request')"
      />
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAutonomyStore } from "@/features/autonomy";
import { useControllerStore } from "@/features/controller/store";

const router = useRouter();
const telemetry = useAutonomyStore();
const controller = useControllerStore();

const controlConnected = computed(() => Boolean(controller.model?.connected));
const canChangeNormalMode = computed(
  () =>
    controlConnected.value &&
    controller.motionControlEnabled &&
    !controller.emergencyStopActive &&
    !controller.motionFault,
);

const modeLabel = computed(() => {
  if (!controller.motionControlEnabled) return "Legacy control";
  return `Mode: ${controller.robotMode}`;
});

const modeSeverity = computed(() => {
  if (controller.robotMode === "estop" || controller.robotMode === "fault") {
    return "danger";
  }
  if (controller.robotMode === "autonomous") return "info";
  if (controller.robotMode === "manual") return "success";
  return "secondary";
});

const enabledSensors = computed(() =>
  telemetry.sensors.filter((sensor) => sensor.enabled),
);
const sensorsReady = computed(
  () =>
    enabledSensors.value.length > 0 &&
    enabledSensors.value.every((sensor) => sensor.running && !sensor.error),
);
const sensorSeverity = computed(() => {
  if (telemetry.sensors.some((sensor) => sensor.error)) return "danger";
  return sensorsReady.value ? "success" : "secondary";
});
const sensorLabel = computed(() => {
  if (telemetry.sensors.some((sensor) => sensor.error)) return "Sensor error";
  if (!enabledSensors.value.length) return "Sensors disabled";
  return sensorsReady.value ? "Sensors ready" : "Sensors waiting";
});
const mappingSeverity = computed(() => {
  if (telemetry.mappingSession?.state === "active") return "success";
  if (telemetry.mappingSession?.state === "paused") return "warning";
  return "secondary";
});
const simulationSeverity = computed(() => {
  const simulation = telemetry.simulation;
  if (!simulation?.enabled) return "secondary";
  if (!simulation.physical_drive_isolated || simulation.error) return "danger";
  return simulation.running ? "success" : "warning";
});
const simulationLabel = computed(() => {
  const simulation = telemetry.simulation;
  if (!simulation?.enabled) return "Simulation disabled";
  if (!simulation.physical_drive_isolated) return "Simulation isolation fault";
  return simulation.running
    ? "Simulation live · isolated"
    : "Simulation stopped";
});

const commandLabel = computed(() => {
  const source = controller.motionSource ?? "unknown";
  if (!controller.direction || controller.speed === 0) {
    return `Source: ${source} · stopped`;
  }
  const direction = controller.direction > 0 ? "forward" : "reverse";
  return `Source: ${source} · ${direction} ${controller.speed.toFixed(0)}%`;
});

const poseLabel = computed(() => {
  const envelope = telemetry.latest.odometry;
  if (!envelope || envelope.channel !== "odometry") return null;
  const { x_m, y_m, linear_speed_mps } = envelope.payload;
  return `Pose: ${x_m.toFixed(2)}, ${y_m.toFixed(2)} m · ${linear_speed_mps.toFixed(2)} m/s`;
});

const safety = computed(() => {
  const envelope = telemetry.latest.safety;
  return envelope?.channel === "safety" ? envelope.payload : null;
});
const safetyBlocked = computed(() => safety.value?.forward_blocked ?? false);
const safetyLabel = computed(() => {
  if (!safety.value) return null;
  if (safety.value.reason) return `Safety: ${safety.value.reason}`;
  return `Safety clear · ${safety.value.max_forward_speed_mps.toFixed(2)} m/s`;
});

const disarm = () => {
  controller.stop();
  controller.setRobotMode("disarmed");
};
</script>
