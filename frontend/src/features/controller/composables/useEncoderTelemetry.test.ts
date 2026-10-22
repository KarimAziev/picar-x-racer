// @vitest-environment jsdom
import { createApp, h, ref, toRaw, nextTick, type App } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  useAutonomyStore,
  type EncoderTelemetry,
} from "@/features/autonomy/store";
import Speedometer from "@/features/controller/components/Speedometer.vue";
import { useRobotStore, useDistanceStore } from "@/features/settings/stores";
import { useEncoderTelemetry } from "./useEncoderTelemetry";

const socket = vi.hoisted(() => ({ cleanup: vi.fn(), init: vi.fn() }));
let connected = ref(true);
vi.mock("@/composables/useWebsocket", () => ({
  useWebSocket: () => ({
    initWS: socket.init,
    cleanup: socket.cleanup,
    connected,
  }),
}));

const header = (sequence: number, seconds: number) => ({
  sequence,
  timestamp_monotonic_ns: seconds * 1e9,
  source_timestamp_ns: null,
  frame_id: "rear_axle",
});

function encoder(sequence: number, seconds: number, ticks: number) {
  const payload: EncoderTelemetry = {
    header: header(sequence, seconds),
    left: null,
    right: null,
    rear_axle_average: { ticks, delta_ticks: 1 },
  };
  useAutonomyStore().latest.encoder = {
    channel: "encoder",
    topic: "/encoder/state",
    payload,
  };
}
function steering() {
  useAutonomyStore().latest.steering = {
    channel: "steering",
    topic: "/steering/position",
    payload: { header: header(1, 1), sensor_angle_deg: 0, wheel_angle_rad: 0 },
  };
}

describe("controller encoder telemetry", () => {
  const apps: App[] = [];
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
    vi.clearAllMocks();
    connected = ref(true);
    const robot = useRobotStore();
    robot.data = structuredClone(toRaw(robot.data));
    robot.data.localization_sensors.steering.enabled = true;
    robot.data.localization_sensors.encoder.enabled = true;
    robot.data.ackermann_odometry = {
      enabled: false,
      wheelbase_m: null,
      wheel_radius_m: 0.05,
      encoder_ticks_per_revolution: 100,
      gear_ratio: 2,
      max_steering_age_ms: 250,
    };
  });
  afterEach(() => {
    apps.splice(0).forEach((app) => app.unmount());
    vi.useRealTimers();
  });
  function mount() {
    let readings!: ReturnType<typeof useEncoderTelemetry>;
    const app = createApp({
      setup() {
        readings = useEncoderTelemetry();
        return () => h("div");
      },
    });
    app.mount(document.createElement("div"));
    apps.push(app);
    return readings;
  }

  it("shows a fresh zero steering angle, hides stale data, and ignores cached samples", () => {
    steering();
    const view = mount();
    expect(view.steering.value).toBeNull();
    steering();
    expect(view.steering.value?.sensor_angle_deg).toBe(0);
    vi.advanceTimersByTime(1000);
    expect(view.steering.value).toBeNull();
    steering();
    expect(view.steering.value).not.toBeNull();
    connected.value = false;
    expect(view.steering.value).toBeNull();
    connected.value = true;
    expect(view.steering.value).toBeNull();
  });

  it("calculates signed speed from cumulative ticks despite skipped sensor messages", () => {
    const view = mount();
    encoder(1, 1, 1000);
    expect(view.encoderSpeedKmh.value).toBeNull();
    encoder(11, 1.5, 1100);
    expect(view.encoderSpeedKmh.value).toBeCloseTo(2 * Math.PI * 0.05 * 3.6);
    encoder(12, 2, 1100);
    expect(view.encoderSpeedKmh.value).toBe(0);
    encoder(22, 2.5, 1000);
    expect(view.encoderSpeedKmh.value).toBeCloseTo(-2 * Math.PI * 0.05 * 3.6);
    vi.advanceTimersByTime(1000);
    expect(view.encoderSpeedKmh.value).toBeNull();
  });

  it("averages paired wheel readings and resets when the encoder roles change", () => {
    const view = mount();
    const store = useAutonomyStore();
    for (const [sequence, seconds, left, right] of [
      [1, 1, 100, 200],
      [2, 1.5, 150, 350],
    ]) {
      store.latest.encoder = {
        channel: "encoder",
        topic: "/encoder/state",
        payload: {
          header: header(sequence!, seconds!),
          rear_axle_average: null,
          left: { ticks: left!, delta_ticks: 1 },
          right: { ticks: right!, delta_ticks: 1 },
        },
      };
    }
    expect(view.encoderSpeedKmh.value).toBeCloseTo(2 * Math.PI * 0.05 * 3.6);
    encoder(3, 2, 900);
    expect(view.encoderSpeedKmh.value).toBeNull();
  });

  it("requires calibration and discards samples across restarts and disconnections", () => {
    const view = mount();
    encoder(10, 10, 100);
    encoder(11, 10.5, 200);
    expect(view.encoderSpeedKmh.value).not.toBeNull();
    encoder(1, 1, 0);
    expect(view.encoderSpeedKmh.value).toBeNull();
    encoder(2, 1.5, 100);
    expect(view.encoderSpeedKmh.value).not.toBeNull();
    connected.value = false;
    expect(view.encoderSpeedKmh.value).toBeNull();
    connected.value = true;
    encoder(3, 2, 200);
    expect(view.encoderSpeedKmh.value).toBeNull();
    useRobotStore().data.ackermann_odometry.wheel_radius_m = null;
    encoder(4, 2.5, 300);
    encoder(5, 3, 400);
    expect(view.encoderSpeedKmh.value).toBeNull();
  });

  it("renders encoder zero ahead of ultrasonic speed and falls back after timeout", async () => {
    useDistanceStore().speed = 2;
    const container = document.createElement("div");
    const app = createApp(Speedometer);
    app.mount(container);
    apps.push(app);
    expect(container.textContent).toContain("Ultrasonic:");
    encoder(1, 1, 100);
    encoder(2, 1.5, 100);
    await nextTick();
    expect(container.textContent).toContain("Encoder:");
    expect(container.textContent).toContain("0 km/h");
    expect(container.textContent).not.toContain("Ultrasonic:");
    vi.advanceTimersByTime(1000);
    await nextTick();
    expect(container.textContent).toContain("Ultrasonic:");
    expect(container.textContent).toContain("2 km/h");
    expect(container.textContent).not.toContain("Encoder:");
  });

  it("hides disabled sensors and shares the connection between mounted consumers", () => {
    const first = mount();
    mount();
    expect(socket.init).toHaveBeenCalledOnce();
    steering();
    useRobotStore().data.localization_sensors.steering.enabled = false;
    expect(first.steering.value).toBeNull();
    apps.pop()!.unmount();
    expect(socket.cleanup).not.toHaveBeenCalled();
    apps.pop()!.unmount();
    expect(socket.cleanup).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });
});
