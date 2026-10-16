// @vitest-environment jsdom

import { createApp, h, type App } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useControllerStore } from "@/features/controller/store";
import { useRobotStore } from "@/features/settings/stores";
import { useJoystickControl } from "./useJoysticManager";

const joystick = vi.hoisted(() => ({
  move: null as
    | ((
        event: unknown,
        data: { angle: { degree: number }; distance: number },
      ) => void)
    | null,
  destroy: vi.fn(),
}));

vi.mock("nipplejs", () => ({
  default: {
    create: () => ({
      on: (event: string, handler: NonNullable<typeof joystick.move>) => {
        if (event === "move") joystick.move = handler;
      },
      destroy: joystick.destroy,
    }),
  },
}));

describe("joystick steering limits", () => {
  let app: App;
  let container: HTMLDivElement;

  beforeEach(() => {
    setActivePinia(createPinia());
    joystick.move = null;
    vi.clearAllMocks();
    container = document.createElement("div");
    document.body.append(container);
  });

  afterEach(() => {
    app.unmount();
    container.remove();
    vi.restoreAllMocks();
  });

  function mountJoystick(minimum: number, maximum: number) {
    const controller = useControllerStore();
    const robot = useRobotStore();
    robot.data.steering_servo = {
      ...robot.data.steering_servo,
      min_angle: minimum,
      max_angle: maximum,
      dec_step: -5,
      inc_step: 5,
    };
    vi.spyOn(controller, "initializeWebSocket").mockImplementation(() => {});
    vi.spyOn(controller, "cleanup").mockImplementation(() => {});
    vi.spyOn(controller, "forward").mockImplementation(() => {});
    vi.spyOn(controller, "backward").mockImplementation(() => {});
    const steering = vi
      .spyOn(controller, "setDirServoAngle")
      .mockImplementation(() => {});
    app = createApp({
      setup() {
        const controls = useJoystickControl(controller, robot);
        return () => h("div", { ref: controls.joystickZone });
      },
    });
    app.mount(container);
    return steering;
  }

  function move(degree: number) {
    expect(joystick.move).not.toBeNull();
    joystick.move?.({}, { angle: { degree }, distance: 20 });
  }

  it("uses full travel independently of keyboard steps", () => {
    const steering = mountJoystick(-15, 15);
    move(0);
    expect(steering).toHaveBeenLastCalledWith(15);
    move(180);
    expect(steering).toHaveBeenLastCalledWith(-15);
    move(60);
    expect(steering).toHaveBeenLastCalledWith(5);
  });

  it("keeps straight forward and reverse centered with asymmetric limits", () => {
    const steering = mountJoystick(-10, 15);
    move(90);
    expect(steering).toHaveBeenLastCalledWith(0);
    move(270);
    expect(steering).toHaveBeenLastCalledWith(-0);
    move(225);
    expect(steering).toHaveBeenLastCalledWith(-5);
    move(315);
    expect(steering).toHaveBeenLastCalledWith(8);
  });
});
