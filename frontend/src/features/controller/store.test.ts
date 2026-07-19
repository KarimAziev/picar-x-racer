// @vitest-environment jsdom

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useControllerStore } from "@/features/controller/store";

const websocket = vi.hoisted(() => ({
  send: vi.fn(),
  cleanup: vi.fn(),
}));

vi.mock("@/composables/useWebsocket", () => ({
  useWebSocket: () => ({
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
  }),
}));

describe("controller motion heartbeat", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    websocket.send.mockClear();
    websocket.cleanup.mockClear();
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
});
