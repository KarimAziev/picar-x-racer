// @vitest-environment jsdom
import { createApp, h, nextTick, toRaw, type App } from "vue";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import ManualMeasurements from "@/features/calibration/ManualMeasurements.vue";
import { useRobotStore } from "@/features/settings/stores";

const { get, patch } = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn() }));
vi.mock("@/api", () => ({ robotApi: { get, patch } }));
let app: App;
let root: HTMLElement;
async function flush() {
  for (let i = 0; i < 8; i++) await Promise.resolve();
  await nextTick();
}
function click(label: string) {
  const button = [...root.querySelectorAll("button")].find((item) =>
    item.textContent?.includes(label),
  );
  if (!button) throw new Error(`Missing button: ${label}`);
  button.click();
}
afterEach(() => {
  app.unmount();
  root.remove();
  vi.resetAllMocks();
});

describe("manual measurement persistence", () => {
  it.each(["sh3001", "lsm9ds1", "lsm6ds33", "mock"] as const)(
    "includes the %s IMU discriminator and preserves measurement precision",
    async (driver) => {
      const pinia = createPinia();
      const store = useRobotStore(pinia);
      store.data = structuredClone(toRaw(store.data));
      store.data.localization_sensors.imu.driver = driver;
      store.data.localization_sensors.imu.transform = {
        x_m: 0.16588,
        y_m: -0.04,
        z_m: 0.0438,
        roll_rad: 0,
        pitch_rad: 0,
        yaw_rad: -Math.PI / 2,
      };
      get.mockResolvedValue(store.data);
      patch.mockResolvedValue({});
      root = document.createElement("div");
      document.body.append(root);
      app = createApp({
        render: () => h(ManualMeasurements, { kind: "mounting" }),
      });
      app.use(pinia);
      app.mount(root);
      const select = root.querySelector("select")!;
      select.value = "imu";
      select.dispatchEvent(new Event("change"));
      await flush();
      click("Review measurements");
      await flush();
      click("Apply measurements");
      await flush();
      expect(patch).toHaveBeenCalledWith(
        "px/api/settings/config",
        {
          localization_sensors: {
            imu: {
              driver,
              transform: {
                x_m: expect.closeTo(0.16588, 10),
                y_m: -0.04,
                z_m: expect.closeTo(0.0438, 10),
                roll_rad: 0,
                pitch_rad: 0,
                yaw_rad: -Math.PI / 2,
              },
            },
          },
        },
        { params: { calibration_step: "imu_mount" } },
      );
      expect(root.textContent).toContain("Measurements saved");
    },
  );

  it("keeps a failed save in review without reporting completion", async () => {
    const pinia = createPinia();
    root = document.createElement("div");
    document.body.append(root);
    app = createApp({
      render: () => h(ManualMeasurements, { kind: "mounting" }),
    });
    app.use(pinia);
    app.mount(root);
    patch.mockRejectedValue(new Error("offline"));
    click("Review measurements");
    await flush();
    click("Apply measurements");
    await flush();
    expect(root.textContent).not.toContain("Measurements saved");
    expect(root.querySelector('[role="alert"]')).not.toBeNull();
    expect(patch).toHaveBeenCalledWith(
      "px/api/settings/config",
      expect.objectContaining({
        localization_sensors: {
          lidar: expect.objectContaining({ driver: "rplidar_c1" }),
        },
      }),
      { params: { calibration_step: "lidar_mount" } },
    );
    expect(get).not.toHaveBeenCalled();
  });
});
