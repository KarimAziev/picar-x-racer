// @vitest-environment jsdom

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useControllerStore } from "@/features/controller/store";
import { useRobotStore, useSettingsStore } from "@/features/settings/stores";

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
    const robot = useRobotStore();
    robot.data = {
      ...robot.data,
      steering_servo: { ...robot.data.steering_servo },
      cam_pan_servo: { ...robot.data.cam_pan_servo },
      cam_tilt_servo: { ...robot.data.cam_tilt_servo },
    };
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

  it("accumulates held-key speed requests without waiting for an echo", () => {
    const store = useControllerStore();
    store.initializeWebSocket();

    store.accelerate();
    store.accelerate();

    expect(websocket.send).toHaveBeenNthCalledWith(1, {
      action: "move",
      payload: { direction: 1, speed: 10 },
    });
    expect(websocket.send).toHaveBeenNthCalledWith(2, {
      action: "move",
      payload: { direction: 1, speed: 20 },
    });
  });

  it("accumulates steering steps without waiting for an echo", () => {
    const store = useControllerStore();
    store.initializeWebSocket();

    store.left();
    store.left();

    expect(websocket.send).toHaveBeenNthCalledWith(1, {
      action: "setServoDirAngle",
      payload: -5,
    });
    expect(websocket.send).toHaveBeenNthCalledWith(2, {
      action: "setServoDirAngle",
      payload: -10,
    });
  });

  for (const servo of [
    {
      field: "steering_servo",
      move: "setDirServoAngle",
      increase: "increaseServoDirCali",
      decrease: "decreaseServoDirCali",
    },
    {
      field: "cam_pan_servo",
      move: "setCamPanAngle",
      increase: "increaseCamPanCali",
      decrease: "decreaseCamPanCali",
    },
    {
      field: "cam_tilt_servo",
      move: "setCamTiltAngle",
      increase: "increaseCamTiltCali",
      decrease: "decreaseCamTiltCali",
    },
  ] as const) {
    for (const reverse of [false, true]) {
      for (const mode of ["sum", "negative"] as const) {
        it(`matches ${servo.field} calibration direction to movement with reverse=${reverse}, mode=${mode}`, () => {
          const robot = useRobotStore();
          const config = robot.data[servo.field];
          config.reverse = reverse;
          config.calibration_mode = mode;
          config.calibration_offset = 4.5;
          const store = useControllerStore();
          store.initializeWebSocket();

          for (const direction of [-1, 1]) {
            store[servo.move](direction * 5);
            const motionCommand = websocket.send.mock.lastCall?.[0];
            const physicalDirection =
              Math.sign(motionCommand.payload) *
              (reverse ? -1 : 1) *
              (mode === "negative" ? -1 : 1);

            store[direction > 0 ? servo.increase : servo.decrease]();
            expect(websocket.send).toHaveBeenLastCalledWith({
              action: physicalDirection > 0 ? servo.increase : servo.decrease,
            });
          }
          expect(config.calibration_offset).toBe(4.5);
        });
      }
    }
  }

  for (const reverse of [false, true]) {
    it(`sends logical steering and camera angles with reverse=${reverse}`, () => {
      const robot = useRobotStore();
      robot.data.steering_servo.reverse = reverse;
      robot.data.cam_pan_servo.reverse = reverse;
      robot.data.cam_tilt_servo.reverse = reverse;
      const store = useControllerStore();
      store.initializeWebSocket();

      store.left();
      store.left();
      expect(websocket.send).toHaveBeenNthCalledWith(1, {
        action: "setServoDirAngle",
        payload: -5,
      });
      expect(websocket.send).toHaveBeenNthCalledWith(2, {
        action: "setServoDirAngle",
        payload: -10,
      });
      store.setCamPanAngle(10);
      expect(websocket.send).toHaveBeenLastCalledWith({
        action: "setCamPanAngle",
        payload: 10,
      });
      store.setCamTiltAngle(-10);
      expect(websocket.send).toHaveBeenLastCalledWith({
        action: "setCamTiltAngle",
        payload: -10,
      });
    });
  }

  for (const motionControlEnabled of [false, true]) {
    it(`keeps logical angles from state updates with motion control=${motionControlEnabled}`, () => {
      const robot = useRobotStore();
      robot.data.steering_servo.reverse = true;
      robot.data.cam_pan_servo.reverse = true;
      robot.data.cam_tilt_servo.reverse = true;
      const store = useControllerStore();
      store.initializeWebSocket();
      store.left();
      websocket.handleMessage?.({
        type: "update",
        payload: {
          servoAngle: -5,
          camPan: 10,
          camTilt: -10,
          motionControlEnabled,
        },
      });
      expect(store.servoAngle).toBe(-5);
      expect(store.camPan).toBe(10);
      expect(store.camTilt).toBe(-10);
      expect(store.requestedServoAngle).toBeNull();
      store.left();
      expect(websocket.send).toHaveBeenLastCalledWith({
        action: "setServoDirAngle",
        payload: -10,
      });
      for (const [type, property, payload] of [
        ["setServoDirAngle", "servoAngle", 5],
        ["setCamPanAngle", "camPan", -10],
        ["setCamTiltAngle", "camTilt", 10],
      ] as const) {
        websocket.handleMessage?.({ type, payload });
        expect(store[property]).toBe(payload);
      }
    });
  }

  it("clamps reversed commands to asymmetric hardware travel limits", () => {
    const robot = useRobotStore();
    for (const field of [
      "steering_servo",
      "cam_pan_servo",
      "cam_tilt_servo",
    ] as const) {
      Object.assign(robot.data[field], {
        reverse: true,
        min_angle: -10,
        max_angle: 30,
      });
    }
    const store = useControllerStore();
    store.initializeWebSocket();
    for (const [method, action] of [
      ["setDirServoAngle", "setServoDirAngle"],
      ["setCamPanAngle", "setCamPanAngle"],
      ["setCamTiltAngle", "setCamTiltAngle"],
    ] as const) {
      store[method](-100);
      expect(websocket.send).toHaveBeenLastCalledWith({ action, payload: -30 });
      store[method](100);
      expect(websocket.send).toHaveBeenLastCalledWith({ action, payload: 10 });
    }
  });

  it("uses the current reverse setting for each calibration step", () => {
    const robot = useRobotStore();
    robot.data.steering_servo.calibration_mode = "sum";
    const store = useControllerStore();
    store.initializeWebSocket();
    store.increaseServoDirCali();
    expect(websocket.send).toHaveBeenLastCalledWith({
      action: "increaseServoDirCali",
    });

    robot.data.steering_servo.reverse = true;
    store.increaseServoDirCali();
    expect(websocket.send).toHaveBeenLastCalledWith({
      action: "decreaseServoDirCali",
    });
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
