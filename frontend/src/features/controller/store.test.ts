// @vitest-environment jsdom

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useControllerStore } from "@/features/controller/store";
import { useSettingsStore } from "@/features/settings/stores";

const websocket = vi.hoisted(() => ({
  send: vi.fn(),
  cleanup: vi.fn(),
  handleMessage: null as ((data: unknown) => void) | null,
}));

vi.mock("@/composables/useWebsocket", () => ({
  useWebSocket: (options: { onMessage?: (data: unknown) => void }) => {
    websocket.handleMessage = options.onMessage ?? null;
    return {
      initWS: vi.fn(),
      send: websocket.send,
      closeWS: vi.fn(),
      cleanup: websocket.cleanup,
      retry: vi.fn(),
      connected: { value: true },
      active: { value: true },
      loading: { value: false },
      reconnectEnabled: { value: true },
      ws: { value: null },
    };
  },
}));

describe("controller motion heartbeat", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    websocket.send.mockClear();
    websocket.cleanup.mockClear();
    websocket.handleMessage = null;
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("refreshes active motion and stops refreshing after stop", () => {
    const store = useControllerStore();
    store.initializeWebSocket();

    store.move(50, 1);
    expect(websocket.send).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(250);
    expect(websocket.send).toHaveBeenCalledTimes(3);
    expect(websocket.send).toHaveBeenLastCalledWith({
      action: "move",
      payload: { direction: 1, speed: 50 },
    });

    store.stop();
    expect(websocket.send).toHaveBeenLastCalledWith({ action: "stop" });
    const callsAfterStop = websocket.send.mock.calls.length;

    vi.advanceTimersByTime(500);
    expect(websocket.send).toHaveBeenCalledTimes(callsAfterStop);
  });

  it("cancels motion heartbeat before sending emergency stop", () => {
    const store = useControllerStore();
    store.initializeWebSocket();
    store.move(50, 1);

    store.emergencyStop("test button");

    expect(websocket.send).toHaveBeenLastCalledWith({
      action: "emergencyStop",
      payload: "test button",
    });
    const callsAfterEstop = websocket.send.mock.calls.length;
    vi.advanceTimersByTime(500);
    expect(websocket.send).toHaveBeenCalledTimes(callsAfterEstop);
  });

  it("accepts controller updates while application settings are incomplete", () => {
    const settingsStore = useSettingsStore();
    Reflect.deleteProperty(settingsStore.data, "robot");
    const store = useControllerStore();
    store.initializeWebSocket();

    expect(() =>
      websocket.handleMessage?.({
        type: "update",
        payload: {
          speed: 0,
          direction: 0,
          servoAngle: 0,
          camPan: 0,
          camTilt: 0,
          maxSpeed: 80,
          distance: 0,
          avoidObstacles: false,
          autoMeasureDistanceMode: false,
          ledBlinking: false,
          motionControlEnabled: false,
          robotMode: "legacy",
          motionGeneration: 0,
          motionReason: null,
          motionSource: null,
          emergencyStop: false,
          motionFault: null,
        },
      }),
    ).not.toThrow();
    expect(store.speed).toBe(0);
  });
});
