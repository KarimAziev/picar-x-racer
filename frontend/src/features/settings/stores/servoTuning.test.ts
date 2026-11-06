// @vitest-environment jsdom
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useControllerStore } from "@/features/controller/store";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";
import { useRobotStore } from "@/features/settings/stores";
import {
  getServoTuning,
  servoTuningError,
} from "@/features/settings/components/calibration/servoTuning";
const { post } = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("@/api", () => ({ robotApi: { post } }));
beforeEach(() => {
  setActivePinia(createPinia());
  post.mockReset();
});
describe("servo tuning previews", () => {
  const servos = [
    ["steering_servo", "increaseServoDirCali", "decreaseServoDirCali"],
    ["cam_pan_servo", "increaseCamPanCali", "decreaseCamPanCali"],
    ["cam_tilt_servo", "increaseCamTiltCali", "decreaseCamTiltCali"],
  ] as const;
  it.each(servos)(
    "uses applied reversal for %s offset shortcuts in both calibration modes",
    async (servo, increase, decrease) => {
      const robot = useRobotStore();
      const controller = useControllerStore();
      const send = vi
        .spyOn(controller, "sendMessage")
        .mockImplementation(() => {});
      for (const mode of ["sum", "negative"] as const) {
        for (const reverse of [true, false]) {
          const config = {
            ...robot.data[servo],
            reverse,
            calibration_mode: mode,
            calibration_offset: 2.5,
          };
          post.mockResolvedValue({ [servo]: config });
          await useServoTuningStore().preview(servo, getServoTuning(config), 0);
          const reversedOffset = reverse !== (mode === "negative");
          controller[increase]();
          expect(send).toHaveBeenLastCalledWith({
            action: reversedOffset ? decrease : increase,
          });
          controller[decrease]();
          expect(send).toHaveBeenLastCalledWith({
            action: reversedOffset ? increase : decrease,
          });
          expect(robot.data[servo].calibration_offset).toBe(2.5);
        }
      }
    },
  );

  it("updates the shared applied limits after an acknowledged preview", async () => {
    const robot = useRobotStore();
    const config = { ...robot.data.steering_servo, max_angle: 45 };
    post.mockResolvedValue({ steering_servo: config });
    await useServoTuningStore().preview(
      "steering_servo",
      getServoTuning(config),
      45,
    );
    expect(post).toHaveBeenCalledWith("px/api/settings/servo-tuning", {
      servo: "steering_servo",
      settings: getServoTuning(config),
      angle: 45,
    });
    expect(robot.data.steering_servo.max_angle).toBe(45);
  });
  it("preserves applied settings after a rejected preview", async () => {
    const robot = useRobotStore();
    const original = robot.data.steering_servo.max_angle;
    post.mockRejectedValue(new Error("Invalid pulse range"));
    await expect(
      useServoTuningStore().preview(
        "steering_servo",
        { ...getServoTuning(robot.data.steering_servo), max_angle: 45 },
        45,
      ),
    ).rejects.toThrow("Invalid pulse range");
    expect(robot.data.steering_servo.max_angle).toBe(original);
    expect(useServoTuningStore().pending).toBe(false);
  });
  it("validates cross-field ranges and signed integer step sizes", () => {
    const settings = getServoTuning(useRobotStore().data.steering_servo);
    expect(servoTuningError(settings)).toBe("");
    expect(
      servoTuningError({ ...settings, min_angle: 40, max_angle: 20 }),
    ).toContain("Minimum angle");
    expect(
      servoTuningError({ ...settings, min_pulse: 2500, max_pulse: 500 }),
    ).toContain("Minimum pulse");
    expect(
      servoTuningError({
        ...settings,
        real_min_angle: 90,
        real_max_angle: -90,
      }),
    ).toContain("Angle at minimum pulse");
    expect(servoTuningError({ ...settings, dec_step: 1 })).not.toBe("");
    expect(servoTuningError({ ...settings, inc_step: 0.5 })).not.toBe("");
  });
});
