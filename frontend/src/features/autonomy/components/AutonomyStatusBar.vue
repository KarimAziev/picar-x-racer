<template>
  <header
    class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-surface-200 bg-surface-0/95 px-3 py-2 shadow-sm dark:border-surface-700 dark:bg-surface-900/95"
  >
    <div class="flex min-w-0 flex-wrap items-center gap-2">
      <Button
        label="Home"
        aria-label="Return to default camera driving view"
        icon="pi pi-home"
        size="small"
        severity="secondary"
        outlined
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
        v-if="motionReason"
        :severity="commandActive ? 'warning' : 'secondary'"
        :value="`Reason: ${motionReason}`"
      />
      <Tag
        v-if="safetyLabel"
        :severity="safetyBlocked ? 'danger' : 'success'"
        :value="safetyLabel"
      />
    </div>

    <div class="flex flex-wrap items-center justify-end gap-2">
      <Button
        v-if="effectiveRobotMode !== 'manual'"
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

const navigationRunning = computed(
  () => telemetry.navigationExecution?.state === "running",
);
const relativeMotionRunning = computed(
  () => telemetry.relativeMotion?.state === "running",
);
const autonomousActionRunning = computed(
  () => navigationRunning.value || relativeMotionRunning.value,
);
const effectiveRobotMode = computed(() =>
  autonomousActionRunning.value ? "autonomous" : controller.robotMode,
);

const modeLabel = computed(() => {
  if (!controller.motionControlEnabled) return "Legacy control";
  return `Mode: ${effectiveRobotMode.value}`;
});

const modeSeverity = computed(() => {
  if (
    effectiveRobotMode.value === "estop" ||
    effectiveRobotMode.value === "fault"
  ) {
    return "danger";
  }
  if (effectiveRobotMode.value === "autonomous") return "info";
  if (effectiveRobotMode.value === "manual") return "success";
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
  const navigation = telemetry.navigationExecution;
  if (navigationRunning.value && navigation) {
    return `Source: autonomy · forward ${navigation.commanded_speed_mps.toFixed(2)} m/s`;
  }
  const relative = telemetry.relativeMotion;
  if (relativeMotionRunning.value && relative) {
    const direction = (relative.distance_m ?? 0) >= 0 ? "forward" : "reverse";
    return `Source: autonomy · ${direction} ${(relative.requested_speed_mps ?? 0).toFixed(2)} m/s`;
  }
  const source = controller.motionSource ?? "unknown";
  if (!controller.direction || controller.speed === 0) {
    return `Source: ${source} · stopped`;
  }
  const direction = controller.direction > 0 ? "forward" : "reverse";
  return `Source: ${source} · ${direction} ${controller.speed.toFixed(0)}%`;
});

const commandActive = computed(
  () => autonomousActionRunning.value || controller.speed !== 0,
);
const motionReason = computed(() => {
  if (navigationRunning.value) return telemetry.navigationExecution?.reason;
  if (relativeMotionRunning.value) return telemetry.relativeMotion?.reason;
  return controller.motionReason;
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
const safetyBlocked = computed(
  () =>
    (safety.value?.forward_blocked ?? false) ||
    (safety.value?.reverse_blocked ?? false),
);
const safetyLabel = computed(() => {
  if (!safety.value) return null;
  if (safety.value.reason) return `Safety: ${safety.value.reason}`;
  return `Safety clear · forward ${safety.value.max_forward_speed_mps.toFixed(2)} m/s · reverse ${safety.value.max_reverse_speed_mps.toFixed(2)} m/s`;
});

const disarm = () => {
  controller.stop();
  controller.setRobotMode("disarmed");
};
</script>
