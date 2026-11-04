// @vitest-environment jsdom

import { createApp, nextTick, ref, type App } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useControllerStore } from "@/features/controller/store";
import JoysticZone from "./JoysticZone.vue";

type JoystickHandler = (event: unknown, data: unknown) => void;
const mocks = vi.hoisted(() => ({
  send: vi.fn(),
  managers: [] as {
    handlers: Record<string, JoystickHandler>;
    destroy: ReturnType<typeof vi.fn>;
  }[],
}));
let connected = ref(true);

vi.mock("@/composables/useWebsocket", () => ({
  useWebSocket: () => ({
    initWS: vi.fn(),
    send: mocks.send,
    cleanup: vi.fn(),
    connected,
    loading: ref(false),
  }),
}));
vi.mock("nipplejs", () => ({
  default: {
    create: () => {
      const manager = {
        handlers: {} as Record<string, JoystickHandler>,
        destroy: vi.fn(),
      };
      mocks.managers.push(manager);
      return {
        on: (event: string, handler: JoystickHandler) => {
          manager.handlers[event] = handler;
        },
        destroy: manager.destroy,
      };
    },
  },
}));

describe("mobile joystick release", () => {
  let app: App | undefined;
  let container: HTMLDivElement;

  beforeEach(() => {
    vi.useFakeTimers();
    mocks.send.mockClear();
    mocks.managers.length = 0;
    connected = ref(true);
    const pinia = createPinia();
    setActivePinia(pinia);
    container = document.createElement("div");
    document.body.append(container);
    app = createApp(JoysticZone);
    app.use(pinia);
    app.mount(container);
  });

  afterEach(() => {
    app?.unmount();
    container.remove();
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const event = (name: string, index = 0, degree = 90) => {
    mocks.managers[index].handlers[name](
      {},
      { angle: { degree }, distance: 20 },
    );
  };
  const startDriving = () => {
    event("start");
    event("move");
    vi.advanceTimersByTime(200);
    expect(mocks.send).toHaveBeenCalledWith({
      action: "move",
      payload: { direction: 1, speed: 40 },
    });
    mocks.send.mockClear();
  };
  const expectStopped = () => {
    const store = useControllerStore();
    expect(mocks.send).toHaveBeenCalledWith({ action: "stop" });
    expect(store.requestedSpeed).toBe(0);
    expect(store.requestedDirection).toBe(0);
    expect(store.motionHeartbeat).toBeNull();
    mocks.send.mockClear();
    vi.advanceTimersByTime(1500);
    expect(
      mocks.send.mock.calls.some(([message]) => message.action === "move"),
    ).toBe(false);
  };

  it("stops on release and does not resend the previous speed", () => {
    startDriving();
    event("end");
    expectStopped();
    event("move");
    expect(
      mocks.send.mock.calls.some(([message]) => message.action === "move"),
    ).toBe(false);
    event("start");
    event("move");
    expect(mocks.send).toHaveBeenCalledWith({
      action: "move",
      payload: { direction: 1, speed: 40 },
    });
  });

  it("stops reverse motion on release", () => {
    event("start");
    event("move", 0, 270);
    expect(mocks.send).toHaveBeenCalledWith({
      action: "move",
      payload: { direction: -1, speed: 40 },
    });
    event("end");
    expectStopped();
  });

  for (const interruption of [
    "blur",
    "pagehide",
    "orientationchange",
    "resize",
  ]) {
    it(`stops immediately on ${interruption} and requires a new gesture`, () => {
      startDriving();
      window.dispatchEvent(new Event(interruption));
      // A queued move from the interrupted gesture must not restart the motor.
      event("move");
      expectStopped();
    });
  }

  it("stops when the page becomes hidden", () => {
    startDriving();
    vi.spyOn(document, "hidden", "get").mockReturnValue(true);
    document.dispatchEvent(new Event("visibilitychange"));
    expectStopped();
  });

  it("does not stop a held throttle when the steering finger is released", () => {
    startDriving();
    event("start", 1);
    event("move", 1, 0);
    event("end", 1);
    expect(mocks.send).not.toHaveBeenCalledWith({ action: "stop" });
    vi.advanceTimersByTime(100);
    expect(mocks.send).toHaveBeenCalledWith({
      action: "move",
      payload: { direction: 1, speed: 40 },
    });
    event("end");
    expectStopped();
  });

  it("stops before unmounting and cancels pending joystick recreation", () => {
    startDriving();
    window.dispatchEvent(new Event("resize"));
    app?.unmount();
    app = undefined;
    expectStopped();
    expect(mocks.managers).toHaveLength(2);
    expect(
      mocks.managers.every(
        (manager) => manager.destroy.mock.calls.length === 1,
      ),
    ).toBe(true);
  });

  it("requires a new gesture after reconnecting", async () => {
    startDriving();
    connected.value = false;
    await nextTick();
    expectStopped();
    connected.value = true;
    await nextTick();
    event("move");
    expect(
      mocks.send.mock.calls.some(([message]) => message.action === "move"),
    ).toBe(false);
  });
});
