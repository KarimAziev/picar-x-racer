// @vitest-environment jsdom
import { createApp, h, ref, nextTick, toRaw, type App } from "vue";
import { createPinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import GuidedCalibration from "@/features/calibration/GuidedCalibration.vue";
import { useRobotStore } from "@/features/settings/stores";
const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/api", () => ({ robotApi: { get, post } }));
let app: App, root: HTMLElement;
let store: ReturnType<typeof useRobotStore>;
const suspended = ref(false);
const status = {
  active: false,
  session_id: null,
  kind: "wheel_distance",
  driving: false,
  elapsed_s: 4,
  max_power_percent: 20,
  encoder_ticks: 120,
  wall_distance_m: 3,
  gyro_radps: 0,
  sensor_angle_deg: 0,
  blockers: [],
  trials: [],
};
async function flush() {
  for (let i = 0; i < 8; i++) await Promise.resolve();
  await nextTick();
}
function button(text: string) {
  const result = [...root.querySelectorAll("button")].find((b) =>
    b.textContent?.includes(text),
  );
  if (!result) throw new Error(`Button not found: ${text}`);
  return result;
}
beforeEach(() => {
  get.mockReset();
  post.mockReset();
  get.mockResolvedValue(status);
  post.mockImplementation(async (path: string) =>
    path.endsWith("/start") || path.endsWith("/heartbeat")
      ? { ...status, active: true, session_id: "owned" }
      : status,
  );
  root = document.createElement("div");
  document.body.append(root);
  suspended.value = false;
  app = createApp({
    setup: () => () => h(GuidedCalibration, { suspended: suspended.value }),
  });
  const pinia = createPinia();
  store = useRobotStore(pinia);
  store.data = structuredClone(toRaw(store.data));
  app.use(pinia);
  app.mount(root);
});
afterEach(() => {
  app.unmount();
  root.remove();
});
describe("guided calibration workflow", () => {
  it("shows saved completion on cards and updates the accessible progress count", async () => {
    expect(
      root.querySelector('[role="progressbar"]')?.getAttribute("aria-valuenow"),
    ).toBe("0");
    store.data.calibration_progress = {
      imu_bias: { "pose_estimation.imu_yaw_bias_radps": 0 },
    };
    await flush();
    expect(
      root.querySelector('[data-guide="imu_bias"]')?.textContent,
    ).toContain("Completed");
    expect(
      root.querySelector('[role="progressbar"]')?.getAttribute("aria-valuenow"),
    ).toBe("1");
    button("Stationary rotation sensor").click();
    await flush();
    expect(root.textContent).toContain("Reviewed measurements saved");
    button("All guides").click();
    await flush();
    expect(
      root.querySelector('[data-guide="imu_bias"]')?.textContent,
    ).toContain("Completed");
    store.data.pose_estimation.imu_yaw_bias_radps = 0.1;
    await flush();
    expect(
      root.querySelector('[data-guide="imu_bias"]')?.textContent,
    ).toContain("Needs review");
    expect(
      root.querySelector('[role="progressbar"]')?.getAttribute("aria-valuenow"),
    ).toBe("0");
  });
  it("cancels an active trial when its section is collapsed", async () => {
    button("Wheel travel").click();
    await flush();
    const ready = root.querySelector<HTMLInputElement>(
      'input[type="checkbox"]',
    )!;
    ready.checked = true;
    ready.dispatchEvent(new Event("change"));
    await flush();
    button("Start trial").click();
    await flush();
    suspended.value = true;
    await flush();
    expect(post).toHaveBeenCalledWith("px/api/calibration/owned/cancel");
    expect(root.querySelector('[aria-current="step"]')?.textContent).toContain(
      "Prepare",
    );
  });
  it("offers preparation, measurement and review without asking for a precise wheel radius", async () => {
    expect(root.textContent).toContain("Body measurements");
    button("Wheel travel").click();
    await flush();
    expect(root.textContent).toContain("Distance between floor marks (cm)");
    expect(root.textContent).toContain("1. Prepare");
    expect(button("Start trial").disabled).toBe(true);
    const ready = root.querySelector<HTMLInputElement>(
      'input[type="checkbox"]',
    )!;
    ready.checked = true;
    ready.dispatchEvent(new Event("change"));
    await flush();
    button("Start trial").click();
    await flush();
    expect(root.querySelector('[aria-current="step"]')?.textContent).toContain(
      "Measure",
    );
    expect(button("Record trial")).toBeTruthy();
    expect(post).toHaveBeenCalledWith(
      "px/api/calibration/start",
      expect.objectContaining({
        kind: "wheel_distance",
        clear_path_confirmed: true,
      }),
    );
    expect(post.mock.calls.some(([path]) => path.endsWith("/apply"))).toBe(
      false,
    );
  });
  it("shows actionable blockers and prevents starting until sensors are ready", async () => {
    get.mockResolvedValue({
      ...status,
      blockers: ["Enable Drive encoders and wait for fresh readings."],
    });
    button("Wheel travel").click();
    await flush();
    const ready = root.querySelector<HTMLInputElement>(
      'input[type="checkbox"]',
    )!;
    ready.checked = true;
    ready.dispatchEvent(new Event("change"));
    await flush();
    expect(root.textContent).toContain("Enable Drive encoders");
    expect(button("Start trial").disabled).toBe(true);
  });
  it("cancels a trial when the window loses focus", async () => {
    button("Wheel travel").click();
    await flush();
    const ready = root.querySelector<HTMLInputElement>(
      'input[type="checkbox"]',
    )!;
    ready.checked = true;
    ready.dispatchEvent(new Event("change"));
    await flush();
    button("Start trial").click();
    await flush();
    window.dispatchEvent(new Event("blur"));
    await flush();
    expect(post).toHaveBeenCalledWith("px/api/calibration/owned/cancel");
    expect(root.textContent).toContain("lost focus");
    expect(button("Start trial").disabled).toBe(true);
  });
  it("cancels the owned trial when the settings panel unmounts", async () => {
    button("Wheel travel").click();
    await flush();
    const ready = root.querySelector<HTMLInputElement>(
      'input[type="checkbox"]',
    )!;
    ready.checked = true;
    ready.dispatchEvent(new Event("change"));
    await flush();
    button("Start trial").click();
    await flush();
    app.unmount();
    await flush();
    expect(post).toHaveBeenCalledWith("px/api/calibration/owned/cancel");
  });
});
