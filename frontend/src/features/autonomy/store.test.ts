import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { ref } from "vue";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  initWS: vi.fn(),
  cleanup: vi.fn(),
  options: null as null | { onMessage?: (message: unknown) => void },
}));

vi.mock("@/api", () => ({
  robotApi: { get: mocks.get },
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
    mocks.get.mockResolvedValue({
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

  it("reports the reactive websocket connection state", () => {
    const store = useAutonomyStore();

    store.initialize();

    expect(store.connected).toBe(true);
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
