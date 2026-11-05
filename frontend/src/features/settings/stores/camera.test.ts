// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useStore } from "./camera";

const { get, handleError } = vi.hoisted(() => ({
  get: vi.fn(),
  handleError: vi.fn(),
}));
vi.mock("@/api", () => ({ appApi: { get } }));
vi.mock("@/features/messager", () => ({
  useMessagerStore: () => ({ handleError }),
}));

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
});

describe("camera metadata recovery", () => {
  it("reports failure and clears fetch errors after a successful retry", async () => {
    const store = useStore();
    get.mockRejectedValue(new Error("Server starting"));
    expect(await store.fetchAllCameraSettings(false)).toBe(false);
    expect(store.settingsError).toContain("Server starting");
    expect(store.devicesError).toContain("Server starting");
    expect(handleError).not.toHaveBeenCalled();
    store.error = "Camera unplugged";
    get.mockImplementation((path: string) =>
      Promise.resolve(
        path.endsWith("devices")
          ? { devices: [] }
          : { width: 640, height: 480 },
      ),
    );
    expect(await store.fetchAllCameraSettings(false)).toBe(true);
    expect(store.fetchError).toBeNull();
    expect(store.error).toBe("Camera unplugged");
    expect(store.data.width).toBe(640);
  });

  it("retains a device-list failure when the settings request succeeds", async () => {
    const store = useStore();
    get.mockImplementation((path: string) =>
      path.endsWith("devices")
        ? Promise.reject(new Error("Device discovery failed"))
        : Promise.resolve({ width: 640 }),
    );
    expect(await store.fetchAllCameraSettings()).toBe(false);
    expect(store.settingsError).toBeNull();
    expect(store.fetchError).toContain("Device discovery failed");
    expect(handleError).toHaveBeenCalledOnce();
  });
});
