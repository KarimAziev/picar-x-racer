// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApp, h, nextTick, reactive, ref, type App } from "vue";
import ImageFeed from "@/ui/ImageFeed.vue";

const mocks = vi.hoisted(() => ({
  camera: { error: null as string | null, fetchAllCameraSettings: vi.fn() },
  initWS: vi.fn(),
  cleanup: vi.fn(),
  stream: {} as Record<string, unknown>,
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
  useWebsocketStream: () => mocks.stream,
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
  vi.clearAllMocks();
  mocks.camera = reactive({
    error: null as string | null,
    fetchAllCameraSettings: vi.fn().mockResolvedValue(undefined),
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
});

describe("ImageFeed availability", () => {
  it("keeps the placeholder height stable during missing-camera retries", async () => {
    mocks.camera.error = "Camera is disconnected";
    const { container } = mountFeed();
    const placeholder = container.querySelector(".scanlines");
    expect(placeholder?.classList.contains("h-[99%]")).toBe(true);

    mocks.camera.error = null;
    await nextTick();

    expect(container.querySelector(".scanlines")).toBe(placeholder);
    expect(placeholder?.classList.contains("h-[99%]")).toBe(true);
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
    expect(container.querySelector(".scanlines")).not.toBeNull();
    expect(image?.style.display).toBe("none");
  });

  it("does not open a stream after settings finish loading for an unmounted feed", async () => {
    let finishLoading: (() => void) | undefined;
    mocks.camera.fetchAllCameraSettings.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          finishLoading = resolve;
        }),
    );
    const { app } = mountFeed();
    app.unmount();
    mountedApps.splice(mountedApps.indexOf(app), 1);

    finishLoading?.();
    await nextTick();

    expect(mocks.initWS).not.toHaveBeenCalled();
  });
});
