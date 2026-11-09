// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import PrimeVue from "primevue/config";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CalibrationModeInfo from "@/features/controller/components/CalibrationModeInfo.vue";
import { useControllerStore } from "@/features/controller/store";
import { usePopupStore } from "@/features/settings/stores";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";

vi.mock(
  "@/features/settings/components/calibration/CalibrationPanel.vue",
  () => ({
    default: defineComponent({
      props: { embedded: Boolean },
      setup: (props) => () =>
        h("div", { "data-embedded": props.embedded }, "Tuning fields"),
    }),
  }),
);

const cleanups: (() => void)[] = [];
beforeEach(() => {
  localStorage.clear();
  setActivePinia(createPinia());
});
afterEach(() => cleanups.splice(0).forEach((cleanup) => cleanup()));

async function mountDialog() {
  const controller = useControllerStore();
  const send = vi.spyOn(controller, "sendMessage").mockImplementation(() => {});
  controller.calibrationMode = true;
  const root = document.createElement("div");
  document.body.append(root);
  const app = createApp(CalibrationModeInfo, { id: "tuning-dialog-test" });
  app.use(PrimeVue, { unstyled: true });
  app.mount(root);
  cleanups.push(() => {
    app.unmount();
    root.remove();
  });
  await nextTick();
  return { controller, send };
}

describe("servo tuning dialog", () => {
  it("stops tuning when Escape closes the dialog", async () => {
    const { send } = await mountDialog();
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", code: "Escape" }),
    );
    await nextTick();
    expect(send).toHaveBeenCalledExactlyOnceWith({ action: "stopServoTuning" });
    await vi.waitFor(() =>
      expect(document.querySelector('[role="dialog"]')).toBeNull(),
    );
  });
  it.each(["Close", "Close tuning"])(
    "stops tuning using %s and can reopen for another session",
    async (label) => {
      const { controller, send } = await mountDialog();
      expect(document.querySelector('[data-embedded="true"]')).not.toBeNull();
      const button = document.querySelector<HTMLButtonElement>(
        `button[aria-label="${label}"]`,
      );
      expect(button).not.toBeNull();
      button?.click();
      await nextTick();
      expect(send).toHaveBeenCalledExactlyOnceWith({
        action: "stopServoTuning",
      });
      await vi.waitFor(() =>
        expect(document.querySelector('[role="dialog"]')).toBeNull(),
      );
      expect(controller.calibrationMode).toBe(true);
      controller.calibrationMode = false;
      await nextTick();
      controller.calibrationMode = true;
      await nextTick();
      expect(document.querySelector('[role="dialog"]')).not.toBeNull();
    },
  );

  it("does not overlay the robot settings while tuning there", async () => {
    usePopupStore().isOpen = true;
    const { send } = await mountDialog();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    usePopupStore().isOpen = false;
    await nextTick();
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
    expect(send).not.toHaveBeenCalled();
  });

  it("waits for an in-flight preview before allowing close", async () => {
    const { send } = await mountDialog();
    const tuning = useServoTuningStore();
    tuning.pending = true;
    await nextTick();
    expect(document.querySelector('button[aria-label="Close"]')).toBeNull();
    const close = document.querySelector<HTMLButtonElement>(
      'button[aria-label="Close tuning"]',
    )!;
    expect(close.disabled).toBe(true);
    close.click();
    expect(send).not.toHaveBeenCalled();
    tuning.pending = false;
    await nextTick();
    close.click();
    expect(send).toHaveBeenCalledExactlyOnceWith({ action: "stopServoTuning" });
  });
});
