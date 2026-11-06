// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick, ref } from "vue";
import { createPinia, setActivePinia } from "pinia";
import PrimeVue from "primevue/config";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ServoTuning from "@/features/settings/components/calibration/ServoTuning.vue";
import { useControllerStore } from "@/features/controller/store";
import { useRobotStore } from "@/features/settings/stores";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";

vi.mock("@/composables/useWebsocket", () => ({
  useWebSocket: () => ({
    initWS: vi.fn(),
    connected: { value: true },
    send: vi.fn(),
  }),
}));
vi.mock("@/ui/NumberInputField.vue", () => ({
  default: defineComponent({
    props: ["field", "modelValue"],
    emits: ["update:modelValue"],
    setup:
      (props, { emit }) =>
      () =>
        h("input", {
          id: props.field,
          value: props.modelValue,
          onInput: (event: Event) => {
            const input = event.target as HTMLInputElement;
            emit(
              "update:modelValue",
              input.value.length ? Number(input.value) : undefined,
            );
          },
        }),
  }),
}));
beforeEach(() => {
  localStorage.clear();
  setActivePinia(createPinia());
});
describe("saving servo tuning drafts", () => {
  it.each([
    ["steering_servo", "setDirServoAngle"],
    ["cam_pan_servo", "setCamPanAngle"],
    ["cam_tilt_servo", "setCamTiltAngle"],
  ] as const)(
    "applies pulse edits when moving %s directly",
    async (name, move) => {
      const pinia = createPinia();
      setActivePinia(pinia);
      const controller = useControllerStore();
      controller.initializeWebSocket();
      controller.calibrationMode = true;
      const robot = useRobotStore();
      robot.data[name] = { ...robot.data[name], enabled: true };
      const preview = vi
        .spyOn(useServoTuningStore(), "preview")
        .mockResolvedValue();
      const movement = vi.spyOn(controller, move);
      const save = vi.spyOn(controller, "saveCalibration");
      const root = document.createElement("div");
      const app = createApp(ServoTuning, { name });
      app.use(pinia);
      app.use(PrimeVue);
      app.provide("isMobile", ref(false));
      app.directive("tooltip", {});
      app.mount(root);
      const input = async (field: string, value: string) => {
        const element = root.querySelector<HTMLInputElement>(
          `#${name}-${field}`,
        )!;
        element.value = value;
        element.dispatchEvent(new Event("input"));
        await nextTick();
      };
      try {
        await input("max_pulse", "2400");
        await input("current", "20");
        expect(preview).toHaveBeenCalledWith(
          name,
          expect.objectContaining({ max_pulse: 2400 }),
          20,
        );
        expect(movement).not.toHaveBeenCalled();
        expect(save).not.toHaveBeenCalled();

        preview.mockClear();
        await input("min_pulse", "2500");
        await input("current", "30");
        expect(preview).not.toHaveBeenCalled();
        expect(movement).not.toHaveBeenCalled();
      } finally {
        app.unmount();
      }
    },
  );

  it("applies fields at the current angle for subsequent keyboard movement", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const controller = useControllerStore();
    controller.initializeWebSocket();
    controller.servoAngle = 12;
    const robot = useRobotStore();
    robot.data.steering_servo = { ...robot.data.steering_servo, enabled: true };
    const preview = vi
      .spyOn(useServoTuningStore(), "preview")
      .mockResolvedValue();
    const root = document.createElement("div");
    const app = createApp(ServoTuning, { name: "steering_servo" });
    app.use(pinia);
    app.use(PrimeVue);
    app.provide("isMobile", ref(false));
    app.directive("tooltip", {});
    app.mount(root);
    try {
      const pulse = root.querySelector<HTMLInputElement>(
        "#steering_servo-max_pulse",
      )!;
      pulse.value = "2400";
      pulse.dispatchEvent(new Event("input"));
      await nextTick();
      const apply = [...root.querySelectorAll("button")].find((button) =>
        button.textContent?.includes("Apply at current angle"),
      );
      expect(apply).toBeDefined();
      apply?.click();
      await nextTick();
      expect(preview).toHaveBeenCalledWith(
        "steering_servo",
        expect.objectContaining({ max_pulse: 2400 }),
        12,
      );
    } finally {
      app.unmount();
    }
  });

  it("applies a reverse-only edit and tests the reversed asymmetric limit", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const controller = useControllerStore();
    controller.initializeWebSocket();
    const robot = useRobotStore();
    robot.data = {
      ...robot.data,
      steering_servo: {
        ...robot.data.steering_servo,
        enabled: true,
        reverse: false,
        min_angle: -10,
        max_angle: 30,
      },
    };
    const preview = vi
      .spyOn(useServoTuningStore(), "preview")
      .mockResolvedValue();
    const root = document.createElement("div");
    const app = createApp(ServoTuning, { name: "steering_servo" });
    app.use(pinia);
    app.use(PrimeVue);
    app.provide("isMobile", ref(false));
    app.directive("tooltip", {});
    const component = app.mount(root) as InstanceType<typeof ServoTuning>;
    try {
      const reverse = root.querySelector<HTMLInputElement>(
        "#steering_servo-reverse",
      )!;
      expect(reverse).not.toBeNull();
      reverse.checked = true;
      reverse.dispatchEvent(new Event("change"));
      await nextTick();
      expect(robot.data.steering_servo.reverse).toBe(false);
      expect(await component.applyDraft()).toBe(true);
      expect(preview).toHaveBeenLastCalledWith(
        "steering_servo",
        expect.objectContaining({ reverse: true }),
        0,
      );
      const minimum = [...root.querySelectorAll("button")].find((button) =>
        button.textContent?.includes("Apply & test minimum"),
      )!;
      minimum.click();
      await nextTick();
      expect(preview).toHaveBeenLastCalledWith(
        "steering_servo",
        expect.objectContaining({ reverse: true }),
        -30,
      );
    } finally {
      app.unmount();
    }
  });

  it("applies edited limits at the current angle before saving", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const controller = useControllerStore();
    controller.initializeWebSocket();
    controller.servoAngle = 12;
    const robot = useRobotStore();
    robot.data = {
      ...robot.data,
      steering_servo: { ...robot.data.steering_servo, enabled: true },
    };
    const preview = vi
      .spyOn(useServoTuningStore(), "preview")
      .mockResolvedValue();
    const root = document.createElement("div");
    const app = createApp(ServoTuning, { name: "steering_servo" });
    app.use(pinia);
    app.use(PrimeVue);
    app.provide("isMobile", ref(false));
    app.directive("tooltip", {});
    const component = app.mount(root) as InstanceType<typeof ServoTuning>;
    try {
      const maximum = root.querySelector<HTMLInputElement>(
        "#steering_servo-max_angle",
      )!;
      maximum.value = "45";
      maximum.dispatchEvent(new Event("input"));
      await nextTick();
      expect(await component.applyDraft()).toBe(true);
      expect(preview).toHaveBeenCalledWith(
        "steering_servo",
        expect.objectContaining({ max_angle: 45 }),
        12,
      );
      preview.mockClear();
      maximum.value = "";
      maximum.dispatchEvent(new Event("input"));
      await nextTick();
      expect(await component.applyDraft()).toBe(false);
      expect(preview).not.toHaveBeenCalled();
    } finally {
      app.unmount();
    }
  });
});
