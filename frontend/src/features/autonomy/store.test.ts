import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { ref } from "vue";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  initWS: vi.fn(),
  cleanup: vi.fn(),
  options: null as null | { onMessage?: (message: unknown) => void },
}));

vi.mock("@/api", () => ({
  robotApi: { get: mocks.get, post: mocks.post },
}));

vi.mock("@/composables/useWebsocket", () => ({
  useWebSocket: (options: { onMessage?: (message: unknown) => void }) => {
    mocks.options = options;
    return {
      initWS: mocks.initWS,
      cleanup: mocks.cleanup,
      closeWS: vi.fn(),
      retry: vi.fn(),
      send: vi.fn(),
      connected: ref(true),
      active: ref(true),
      loading: ref(false),
      reconnectEnabled: ref(true),
      ws: ref(null),
    };
  },
}));

import { useAutonomyStore } from "@/features/autonomy/store";

describe("autonomy telemetry store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.options = null;
    mocks.get.mockImplementation((path: string) => {
      if (path === "/px/api/map/session") {
        return Promise.resolve({
          enabled: true,
          state: "idle",
          session_id: 0,
          map_sequence: 0,
          scans_received: 0,
          scans_inserted: 0,
          returns_inserted: 0,
          ignored_inactive_scans: 0,
          rejected_missing_odometry: 0,
          rejected_stale_odometry: 0,
          has_map: false,
        });
      }
      if (path === "/px/api/map/current") {
        return Promise.resolve({
          header: {
            sequence: 1,
            frame_id: "odom",
            timestamp_monotonic_ns: 1,
            source_timestamp_ns: null,
          },
          width: 1,
          height: 1,
          resolution_m: 0.1,
          origin_x_m: 0,
          origin_y_m: 0,
          origin_yaw_rad: 0,
          data: [-1],
        });
      }
      if (path === "/px/api/autonomy/relative-motion") {
        return Promise.resolve({ available: true, state: "idle" });
      }
      return Promise.resolve({
        sensors: [
          {
            sensor: "imu",
            enabled: true,
            running: true,
            published_messages: 12,
            last_timestamp_monotonic_ns: 100,
            error: null,
          },
        ],
      });
    });
  });

  it("fetches publisher status", async () => {
    const store = useAutonomyStore();

    await store.refreshStatus();

    expect(mocks.get).toHaveBeenCalledWith("/px/api/sensors/status");
    expect(store.sensors[0].published_messages).toBe(12);
  });

  it("keeps the newest telemetry envelope by channel", () => {
    const store = useAutonomyStore();
    store.initialize();

    mocks.options?.onMessage?.({
      channel: "encoder",
      topic: "/encoder/state",
      payload: {
        header: {
          sequence: 2,
          frame_id: "encoder",
          timestamp_monotonic_ns: 200,
          source_timestamp_ns: 190,
        },
        left: { ticks: 42, delta_ticks: 3 },
        right: { ticks: 44, delta_ticks: 5 },
      },
    });

    expect(mocks.initWS).toHaveBeenCalledOnce();
    expect(store.latest.encoder?.payload).toMatchObject({
      left: { ticks: 42, delta_ticks: 3 },
      right: { ticks: 44, delta_ticks: 5 },
    });

    store.cleanup();
    expect(mocks.cleanup).toHaveBeenCalledOnce();
  });

  it("retrieves and operates the explicit mapping session", async () => {
    const store = useAutonomyStore();
    mocks.post.mockResolvedValue({
      enabled: true,
      state: "active",
      session_id: 1,
      map_sequence: 0,
      scans_received: 0,
      scans_inserted: 0,
      returns_inserted: 0,
      ignored_inactive_scans: 0,
      rejected_missing_odometry: 0,
      rejected_stale_odometry: 0,
      has_map: false,
    });

    await store.refreshMappingSession();
    await store.runMappingAction("start");
    await store.runMappingAction("clear");

    expect(mocks.get).toHaveBeenCalledWith("/px/api/map/session");
    expect(mocks.post).toHaveBeenCalledWith("/px/api/map/session/start");
    expect(mocks.post).toHaveBeenCalledWith("/px/api/map/session/clear");
    expect(store.mappingSession?.state).toBe("active");
    expect(store.mappingSession?.session_id).toBe(1);
    expect(store.mapClearGeneration).toBe(1);
  });

  it("reports the reactive websocket connection state", () => {
    const store = useAutonomyStore();

    store.initialize();

    expect(store.connected).toBe(true);
  });

  it("starts a relative-distance action with SI values", async () => {
    const store = useAutonomyStore();
    mocks.post.mockResolvedValue({
      available: true,
      state: "running",
      action_id: "action-1",
      distance_m: 0.5,
      requested_speed_mps: 0.15,
      progress_m: 0,
      remaining_m: 0.5,
      reason: null,
    });

    await store.refreshRelativeMotion();
    await store.startRelativeDistance(0.5, 0.15);

    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/relative-motion/distance",
      { distance_m: 0.5, speed_mps: 0.15 },
    );
    expect(store.relativeMotion?.state).toBe("running");
  });

  it("starts a relative steering arc with SI distance and speed", async () => {
    const store = useAutonomyStore();
    mocks.post.mockResolvedValue({
      available: true,
      state: "running",
      action_id: "arc-1",
      action_type: "arc",
      distance_m: 0.3,
      requested_speed_mps: 0.12,
      progress_m: 0,
      remaining_m: 0.3,
      steering_angle_deg: -15,
      target_yaw_rad: -0.32,
      yaw_progress_rad: 0,
      reason: null,
    });

    await store.startRelativeArc(0.3, 0.12, -15);

    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/relative-motion/arc",
      {
        distance_m: 0.3,
        speed_mps: 0.12,
        steering_angle_deg: -15,
      },
    );
    expect(store.relativeMotion?.action_type).toBe("arc");
  });

  it("keeps a shared telemetry connection until its last consumer leaves", () => {
    const store = useAutonomyStore();

    store.initialize();
    store.initialize();
    store.cleanup();

    expect(store.consumers).toBe(1);
    expect(mocks.cleanup).not.toHaveBeenCalled();

    store.cleanup();
    expect(store.consumers).toBe(0);
    expect(mocks.cleanup).toHaveBeenCalledOnce();
  });
});
