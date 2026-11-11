// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import PrimeVue from "primevue/config";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CalibrationModeInfo from "@/features/controller/components/CalibrationModeInfo.vue";
import { useControllerStore } from "@/features/controller/store";
import { usePopupStore } from "@/features/settings/stores";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";

const { applyDrafts } = vi.hoisted(() => ({ applyDrafts: vi.fn() }));

vi.mock("@/features/settings/components/calibration/Servos.vue", () => ({
  default: defineComponent({
    setup: (_, { expose }) => {
      expose({ applyDrafts });
      return () => h("div", "Servo fields");
    },
  }),
}));
vi.mock("@/features/settings/components/calibration/Motors.vue", () => ({
  default: defineComponent({ setup: () => () => h("div", "Motor fields") }),
}));
vi.mock("@/ui/SelectField.vue", () => ({
  default: defineComponent({ setup: () => () => h("div", "Modifier") }),
}));

const cleanups: (() => void)[] = [];
beforeEach(() => {
  applyDrafts.mockReset().mockResolvedValue(true);
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
  it("keeps a single set of tuning actions in the dialog footer", async () => {
    const controller = useControllerStore();
    const reset = vi
      .spyOn(controller, "resetCalibration")
      .mockImplementation(() => {});
    const toggle = vi
      .spyOn(controller, "toggleCalibration")
      .mockImplementation(() => {});
    await mountDialog();
    const footer = document.querySelector(
      '[data-pc-name="dialog"] > [data-pc-section="footer"]',
    )!;
    [
      "Reset offsets & directions",
      "Stop keyboard tuning",
      "Save tuning",
      "Close tuning",
    ].forEach((label) => {
      expect(
        document.querySelectorAll(`button[aria-label="${label}"]`),
      ).toHaveLength(1);
      expect(
        footer.contains(
          document.querySelectorAll(`button[aria-label="${label}"]`)[0],
        ),
      ).toBe(true);
    });
    document
      .querySelectorAll<HTMLButtonElement>(
        'button[aria-label="Reset offsets & directions"]',
      )[0]!
      .click();
    document
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Stop keyboard tuning"]',
      )!
      .click();
    expect(reset).toHaveBeenCalledOnce();
    expect(toggle).toHaveBeenCalledOnce();
  });

  it("applies drafts before saving from the footer and keeps tuning open", async () => {
    const { controller } = await mountDialog();
    const save = vi
      .spyOn(controller, "saveCalibration")
      .mockImplementation(() => {});
    let finish = (_valid: boolean) => {};
    applyDrafts.mockImplementation(
      () =>
        new Promise<boolean>((resolve) => {
          finish = resolve;
        }),
    );
    const button = document.querySelector<HTMLButtonElement>(
      'button[aria-label="Save tuning"]',
    )!;
    button.click();
    await nextTick();
    expect(applyDrafts).toHaveBeenCalledOnce();
    expect(save).not.toHaveBeenCalled();
    expect(button.disabled).toBe(true);
    button.click();
    expect(applyDrafts).toHaveBeenCalledOnce();
    finish(true);
    await vi.waitFor(() => expect(save).toHaveBeenCalledOnce());
    await vi.waitFor(() => expect(button.disabled).toBe(false));
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
  });

  it("does not save invalid drafts or save during a pending preview", async () => {
    const { controller } = await mountDialog();
    const save = vi
      .spyOn(controller, "saveCalibration")
      .mockImplementation(() => {});
    const tuning = useServoTuningStore();
    const button = document.querySelector<HTMLButtonElement>(
      'button[aria-label="Save tuning"]',
    )!;
    tuning.pending = true;
    await nextTick();
    expect(button.disabled).toBe(true);
    button.click();
    expect(applyDrafts).not.toHaveBeenCalled();
    tuning.pending = false;
    applyDrafts.mockResolvedValue(false);
    await nextTick();
    button.click();
    await nextTick();
    expect(applyDrafts).toHaveBeenCalledOnce();
    expect(save).not.toHaveBeenCalled();
    await vi.waitFor(() => expect(button.disabled).toBe(false));
  });

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
      expect(document.querySelector("#tuning-dialog-test")).not.toBeNull();
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
