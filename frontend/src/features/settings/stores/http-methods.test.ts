// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useStore as useCameraStore } from "@/features/settings/stores/camera";
import { useStore as useSettingsStore } from "@/features/settings/stores/settings";

const { getMock, postMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
}));

vi.mock("@/api", () => ({
  appApi: {
    get: getMock,
    post: postMock,
  },
}));

describe("state-changing endpoint methods", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("uses POST for host power actions", async () => {
    const store = useSettingsStore();

    await store.shutdown();
    await store.restart();

    expect(postMock).toHaveBeenNthCalledWith(1, "/api/system/shutdown");
    expect(postMock).toHaveBeenNthCalledWith(2, "/api/system/restart");
    expect(getMock).not.toHaveBeenCalled();
  });

  it("uses POST to capture and persist a photo", async () => {
    postMock.mockResolvedValue({ file: "photo.jpg" });
    const store = useCameraStore();

    const filename = await store.capturePhoto();

    expect(filename).toBe("photo.jpg");
    expect(postMock).toHaveBeenCalledWith("/api/camera/capture-photo");
    expect(getMock).not.toHaveBeenCalled();
  });
});

describe("photo presets", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("captures the selected preset with time for camera restoration", async () => {
    postMock.mockResolvedValue({ file: "high.jpg" });
    const settings = useSettingsStore();
    settings.data.photo.selected_preset_id = "high";
    const store = useCameraStore();
    expect(
      await store.capturePhoto(settings.data.photo.selected_preset_id),
    ).toBe("high.jpg");
    expect(postMock).toHaveBeenCalledWith(
      "/api/camera/capture-photo",
      { preset_id: "high" },
      { timeout: 60000 },
    );
    expect(store.capturing).toBe(false);
  });

  it("does not submit duplicate captures while the camera is busy", async () => {
    const store = useCameraStore();
    store.capturing = true;
    expect(await store.capturePhoto()).toBeUndefined();
    expect(postMock).not.toHaveBeenCalled();
  });

  it("persists preset deletion and snapshot selection", async () => {
    const photo = { presets: [], selected_preset_id: null };
    postMock.mockResolvedValue({ photo });
    const store = useSettingsStore();
    expect(await store.savePhotoSettings(photo)).toBe(true);
    expect(postMock).toHaveBeenCalledWith("/api/settings", { photo });
    expect(useSettingsStore().data.photo).toEqual(photo);
    expect(store.savingPhotoSettings).toBe(false);
  });
});
