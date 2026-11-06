// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import CalibrationOffset from "@/features/settings/components/calibration/CalibrationOffset.vue";
import { useControllerStore } from "@/features/controller/store";
import { useRobotStore } from "@/features/settings/stores";

vi.mock("@/ui/NumberInputField.vue", () => ({
  default: defineComponent({ setup: () => () => h("div") }),
}));
vi.mock("@/features/settings/components/calibration/ServoInput.vue", () => ({
  default: defineComponent({
    props: ["value", "config"],
    emits: ["update:modelValue"],
    setup:
      (props, { emit }) =>
      () =>
        h(
          "button",
          { onClick: () => emit("update:modelValue", 15) },
          `${props.value}/${props.config.max_angle}`,
        ),
  }),
}));
describe("settings servo value", () => {
  it.each([
    ["steering_servo", "servoAngle", "setDirServoAngle"],
    ["cam_pan_servo", "camPan", "setCamPanAngle"],
    ["cam_tilt_servo", "camTilt", "setCamTiltAngle"],
  ] as const)(
    "tracks controller acknowledgements and replaced %s settings",
    async (servo, gauge, action) => {
      const pinia = createPinia();
      setActivePinia(pinia);
      const controller = useControllerStore();
      const robot = useRobotStore();
      const move = vi.spyOn(controller, action).mockImplementation(() => {});
      const root = document.createElement("div");
      const app = createApp(CalibrationOffset, {
        field: `${servo}.calibration_offset`,
        modelValue: 0,
      });
      app.use(pinia);
      app.mount(root);
      try {
        root.querySelector("button")?.click();
        expect(move).toHaveBeenCalledWith(15);
        controller[gauge] = 15;
        robot.data = {
          ...robot.data,
          [servo]: { ...robot.data[servo], max_angle: 60 },
        };
        await nextTick();
        expect(root.querySelector("button")?.textContent).toBe("15/60");
      } finally {
        app.unmount();
      }
    },
  );
});
