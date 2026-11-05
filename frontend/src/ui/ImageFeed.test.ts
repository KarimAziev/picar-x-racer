// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApp, h, nextTick, reactive, ref, type App } from "vue";
import type { WebsocketStreamParams } from "@/features/detection/composables/useWebsocketStream";
import ImageFeed from "@/ui/ImageFeed.vue";

const mocks = vi.hoisted(() => ({
  camera: {
    error: null as string | null,
    fetchAllCameraSettings: vi.fn(),
    fetchError: null as string | null,
  },
  initWS: vi.fn(),
  cleanup: vi.fn(),
  stream: {} as Record<string, unknown>,
  streamOptions: {} as WebsocketStreamParams,
}));

vi.mock("@/features/settings/stores", () => ({
  useCameraStore: () => mocks.camera,
  useThemeStore: () => ({}),
}));

vi.mock("@/features/detection", () => ({
  useDetectionStore: () => ({
    data: { active: false },
    cleanup: vi.fn(),
  }),
  useWebsocketStream: (options: WebsocketStreamParams) => {
    mocks.streamOptions = options;
    return mocks.stream;
  },
}));

vi.mock("@/features/detection/config", () => ({
  overlayStyleHandlers: {},
}));

vi.mock("@/composables/useCameraRotate", () => ({
  useCameraRotate: () => ({
    addListeners: vi.fn(),
    removeListeners: vi.fn(),
  }),
}));

const mountedApps: App[] = [];
let active = ref(false);
let imgLoading = ref(true);

const mountFeed = () => {
  const container = document.createElement("div");
  const app = createApp({ render: () => h(ImageFeed) });
  app.mount(container);
  mountedApps.push(app);
  return { container, app };
};

beforeEach(() => {
  vi.useFakeTimers();
  vi.clearAllMocks();
  mocks.camera = reactive({
    error: null as string | null,
    fetchAllCameraSettings: vi.fn().mockResolvedValue(true),
    fetchError: null as string | null,
  });
  active = ref(false);
  imgLoading = ref(true);
  mocks.stream = {
    initWS: mocks.initWS,
    cleanup: mocks.cleanup,
    handleImageOnLoad: () => {
      imgLoading.value = false;
    },
    imgLoading,
    active,
    imgInitted: ref(false),
  };
});

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount());
  vi.useRealTimers();
});

describe("ImageFeed availability", () => {
  it("collapses errors to a line and keeps retries from flashing scan lines", async () => {
    mocks.camera.error = "Camera is disconnected";
    const { container } = mountFeed();
    expect(container.querySelector(".scanlines")).toBeNull();
    const line = container.querySelector('[data-testid="camera-offline-line"]');
    expect(line).not.toBeNull();
    expect(container.querySelector('[role="status"]')?.textContent).toContain(
      "Camera is disconnected",
    );

    mocks.camera.error = null;
    await nextTick();
    expect(container.querySelector(".scanlines")).toBeNull();
    expect(container.querySelector('[data-testid="camera-offline-line"]')).toBe(
      line,
    );
    expect(container.querySelector('[role="status"]')?.textContent).toContain(
      "Camera is disconnected",
    );
  });

  it("keeps the placeholder visible until the first frame has decoded", async () => {
    const { container } = mountFeed();
    const image = container.querySelector("img");
    expect(image).not.toBeNull();
    expect(image?.style.display).toBe("none");

    active.value = true;
    await nextTick();
    expect(container.querySelector(".scanlines")).not.toBeNull();
    expect(image?.style.display).toBe("none");

    image?.dispatchEvent(new Event("load"));
    await nextTick();
    expect(container.querySelector(".scanlines")).toBeNull();
    expect(image?.style.display).not.toBe("none");

    mocks.camera.error = "Camera is disconnected";
    await nextTick();
    expect(container.querySelector(".scanlines")).toBeNull();
    expect(
      container.querySelector('[data-testid="camera-offline-line"]'),
    ).not.toBeNull();
    expect(image?.style.display).toBe("none");

    mocks.camera.error = null;
    await nextTick();
    expect(image?.style.display).toBe("none");
    expect(container.querySelector(".scanlines")).toBeNull();

    mocks.camera.error = "Previous camera error";
    await nextTick();
    image?.dispatchEvent(new Event("load"));
    await nextTick();
    expect(mocks.camera.error).toBeNull();
    expect(image?.style.display).not.toBe("none");
  });

  it("starts streaming while metadata loads and cancels metadata retries on unmount", async () => {
    let finishLoading!: (loaded: boolean) => void;
    mocks.camera.fetchAllCameraSettings.mockImplementation(
      () =>
        new Promise<boolean>((resolve) => {
          finishLoading = resolve;
        }),
    );
    const { app } = mountFeed();
    expect(mocks.initWS).toHaveBeenCalledOnce();
    app.unmount();
    mountedApps.splice(mountedApps.indexOf(app), 1);
    finishLoading(false);
    await vi.advanceTimersByTimeAsync(10000);
    expect(mocks.camera.fetchAllCameraSettings).toHaveBeenCalledOnce();
    expect(mocks.cleanup).toHaveBeenCalledOnce();
  });

  it("retries failed metadata requests without restarting the stream", async () => {
    mocks.camera.fetchAllCameraSettings
      .mockResolvedValueOnce(false)
      .mockResolvedValue(true);
    mountFeed();
    await vi.advanceTimersByTimeAsync(5000);
    expect(mocks.camera.fetchAllCameraSettings).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(10000);
    expect(mocks.camera.fetchAllCameraSettings).toHaveBeenCalledTimes(2);
    expect(mocks.initWS).toHaveBeenCalledOnce();
  });

  it("collapses a disconnected stream and stays collapsed until a decoded frame", async () => {
    const { container } = mountFeed();
    mocks.streamOptions.onClose?.();
    await nextTick();
    expect(container.querySelector(".scanlines")).toBeNull();
    expect(
      container.querySelector('[data-testid="camera-offline-line"]'),
    ).not.toBeNull();
    active.value = true;
    await nextTick();
    expect(
      container.querySelector('[data-testid="camera-offline-line"]'),
    ).not.toBeNull();
    container.querySelector("img")?.dispatchEvent(new Event("load"));
    await nextTick();
    expect(
      container.querySelector('[data-testid="camera-offline-line"]'),
    ).toBeNull();
  });
});
