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
