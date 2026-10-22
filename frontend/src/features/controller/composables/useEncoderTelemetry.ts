import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import {
  useAutonomyStore,
  type EncoderTelemetry,
} from "@/features/autonomy/store";
import { useRobotStore } from "@/features/settings/stores";

const MAX_READING_AGE_MS = 1000;

function meanTicks(reading: EncoderTelemetry): number | null {
  if (reading.rear_axle_average) return reading.rear_axle_average.ticks;
  const wheels = [reading.left, reading.right].filter((wheel) => wheel != null);
  if (!wheels.length) return null;
  return (
    wheels.reduce((total, wheel) => total + wheel.ticks, 0) / wheels.length
  );
}

function sameEncoders(a: EncoderTelemetry, b: EncoderTelemetry): boolean {
  return (["left", "right", "rear_axle_average"] as const).every(
    (role) => Boolean(a[role]) === Boolean(b[role]),
  );
}

/** Live controller readings; speed uses cumulative counts across telemetry samples. */
export function useEncoderTelemetry() {
  const telemetry = useAutonomyStore();
  const robot = useRobotStore();
  const now = ref(Date.now());
  const steeringReceivedAt = ref<number | null>(null);
  const encoderReceivedAt = ref<number | null>(null);
  const measuredSpeed = ref<number | null>(null);
  let previousEncoder: EncoderTelemetry | null = null;
  let timer: ReturnType<typeof setInterval> | undefined;

  const fresh = (receivedAt: number | null) =>
    telemetry.connected &&
    receivedAt !== null &&
    now.value - receivedAt < MAX_READING_AGE_MS;

  const resetEncoder = () => {
    previousEncoder = null;
    encoderReceivedAt.value = null;
    measuredSpeed.value = null;
  };

  watch(
    () => telemetry.connected,
    () => {
      steeringReceivedAt.value = null;
      resetEncoder();
    },
    { flush: "sync" },
  );

  watch(
    () => telemetry.latest.steering,
    (message) => {
      if (message?.channel !== "steering" || !telemetry.connected) return;
      now.value = Date.now();
      steeringReceivedAt.value = now.value;
    },
    { flush: "sync" },
  );

  watch(
    () => [
      robot.data.localization_sensors.encoder.enabled,
      robot.data.ackermann_odometry.wheel_radius_m,
      robot.data.ackermann_odometry.encoder_ticks_per_revolution,
      robot.data.ackermann_odometry.gear_ratio,
    ],
    resetEncoder,
    { flush: "sync" },
  );

  watch(
    () => telemetry.latest.encoder,
    (message) => {
      if (message?.channel !== "encoder" || !telemetry.connected) return;
      now.value = Date.now();
      const previous = fresh(encoderReceivedAt.value) ? previousEncoder : null;
      const current = message.payload;
      previousEncoder = current;
      encoderReceivedAt.value = now.value;
      measuredSpeed.value = null;
      if (
        !previous ||
        !sameEncoders(previous, current) ||
        previous.header.frame_id !== current.header.frame_id ||
        current.header.sequence <= previous.header.sequence
      )
        return;

      const elapsedSeconds =
        (current.header.timestamp_monotonic_ns -
          previous.header.timestamp_monotonic_ns) /
        1e9;
      if (elapsedSeconds <= 0 || elapsedSeconds > MAX_READING_AGE_MS / 1000)
        return;
      const {
        wheel_radius_m: radius,
        encoder_ticks_per_revolution: resolution,
        gear_ratio: ratio,
      } = robot.data.ackermann_odometry;
      if (
        radius === null ||
        resolution === null ||
        ![radius, resolution, ratio].every(
          (value) => Number.isFinite(value) && value > 0,
        )
      )
        return;
      const ticks = meanTicks(current);
      const previousTicks = meanTicks(previous);
      if (ticks === null || previousTicks === null) return;
      // Websocket delivery may skip samples; delta_ticks covers only one sensor interval.
      const speed =
        (((ticks - previousTicks) * 2 * Math.PI * radius) /
          (resolution * ratio * elapsedSeconds)) *
        3.6;
      if (Number.isFinite(speed)) measuredSpeed.value = speed;
    },
    { flush: "sync" },
  );

  const steering = computed(() => {
    const message = telemetry.latest.steering;
    return robot.data.localization_sensors.steering.enabled &&
      fresh(steeringReceivedAt.value) &&
      message?.channel === "steering" &&
      Number.isFinite(message.payload.sensor_angle_deg) &&
      Number.isFinite(message.payload.wheel_angle_rad)
      ? message.payload
      : null;
  });

  const encoderSpeedKmh = computed(() =>
    robot.data.localization_sensors.encoder.enabled &&
    fresh(encoderReceivedAt.value)
      ? measuredSpeed.value
      : null,
  );

  onMounted(() => {
    telemetry.initializeTelemetry();
    timer = setInterval(() => {
      now.value = Date.now();
    }, 100);
  });
  onUnmounted(() => {
    clearInterval(timer);
    telemetry.cleanup();
  });

  return { steering, encoderSpeedKmh };
}
