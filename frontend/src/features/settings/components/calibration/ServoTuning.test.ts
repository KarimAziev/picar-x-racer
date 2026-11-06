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
