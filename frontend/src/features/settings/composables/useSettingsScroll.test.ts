// @vitest-environment jsdom
import { createApp, defineComponent, h, nextTick, ref } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsTab } from "@/features/settings/enums";
import { useStore as usePopupStore } from "@/features/settings/stores/popup";
import { useSettingsScroll } from "@/features/settings/composables/useSettingsScroll";

let resize = () => {};
const disconnect = vi.fn();
const cleanups: (() => void)[] = [];

beforeEach(() => {
  localStorage.clear();
  setActivePinia(createPinia());
  vi.useFakeTimers();
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) =>
    setTimeout(() => callback(0), 16),
  );
  vi.stubGlobal("cancelAnimationFrame", clearTimeout);
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(callback: () => void) {
        resize = callback;
      }
      observe() {}
      disconnect = disconnect;
    },
  );
  disconnect.mockClear();
});

afterEach(() => {
  cleanups.splice(0).forEach((cleanup) => cleanup());
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

async function renderFrame() {
  await nextTick();
  vi.runOnlyPendingTimers();
  await nextTick();
}

function mountSettings(maximumScroll = 2000) {
  const store = usePopupStore();
  store.isOpen = true;
  const viewport = document.createElement("div");
  viewport.className = "p-dialog-content";
  document.body.append(viewport);
  let top = 0;
  let maximum = maximumScroll;
  Object.defineProperties(viewport, {
    clientHeight: { get: () => 500 },
    scrollHeight: { get: () => maximum + 500 },
    scrollTop: {
      get: () => top,
      set: (value: number) => {
        top = Math.min(maximum, Math.max(0, value));
      },
    },
  });
  const app = createApp(
    defineComponent({
      setup() {
        const content = ref<HTMLElement | null>(null);
        useSettingsScroll(content);
        return () => h("div", { ref: content });
      },
    }),
  );
  app.mount(viewport);
  const unmount = () => {
    app.unmount();
    viewport.remove();
  };
  cleanups.push(unmount);
  return {
    viewport,
    store,
    scrollTo(value: number) {
      viewport.scrollTop = value;
      viewport.dispatchEvent(new Event("scroll"));
    },
    resize(max: number) {
      maximum = max;
      top = Math.min(top, max);
      resize();
    },
    unmount() {
      cleanups.splice(cleanups.indexOf(unmount), 1);
      unmount();
    },
  };
}

describe("settings scroll positions", () => {
  it("remembers independent tab positions and restores after reopening", async () => {
    const settings = mountSettings();
    await renderFrame();
    settings.scrollTo(450);
    settings.store.tab = SettingsTab.ROBOT;
    await renderFrame();
    expect(settings.viewport.scrollTop).toBe(0);
    settings.scrollTo(900);
    settings.store.tab = SettingsTab.GENERAL;
    await renderFrame();
    expect(settings.viewport.scrollTop).toBe(450);
    settings.store.isOpen = false;
    settings.unmount();
    const reopened = mountSettings();
    await renderFrame();
    expect(reopened.viewport.scrollTop).toBe(450);
    reopened.store.tab = SettingsTab.ROBOT;
    await renderFrame();
    expect(reopened.viewport.scrollTop).toBe(900);
  });

  it("persists positions across store recreation", async () => {
    const settings = mountSettings();
    await renderFrame();
    settings.scrollTo(735);
    settings.store.isOpen = false;
    await nextTick();
    settings.unmount();
    settings.store.$dispose();
    setActivePinia(createPinia());
    const reopened = mountSettings();
    await renderFrame();
    expect(reopened.viewport.scrollTop).toBe(735);
  });

  it("waits for asynchronous content without saving clamped intermediate positions", async () => {
    usePopupStore().scrollPositions[SettingsTab.GENERAL] = 1200;
    const settings = mountSettings(0);
    await renderFrame();
    settings.scrollTo(0);
    settings.resize(600);
    await renderFrame();
    settings.scrollTo(600);
    expect(settings.store.scrollPositions[SettingsTab.GENERAL]).toBe(1200);
    settings.resize(1800);
    await renderFrame();
    expect(settings.viewport.scrollTop).toBe(1200);
  });

  it("preserves a pending target if closed before loading finishes", async () => {
    usePopupStore().scrollPositions[SettingsTab.GENERAL] = 1200;
    const settings = mountSettings(0);
    await renderFrame();
    settings.store.isOpen = false;
    settings.unmount();
    expect(settings.store.scrollPositions[SettingsTab.GENERAL]).toBe(1200);
    expect(disconnect).toHaveBeenCalledOnce();
    const reopened = mountSettings();
    await renderFrame();
    expect(reopened.viewport.scrollTop).toBe(1200);
  });

  it.each(["wheel", "touchstart", "pointerdown", "keydown"])(
    "lets %s interaction override pending restoration",
    async (event) => {
      usePopupStore().scrollPositions[SettingsTab.GENERAL] = 1200;
      const settings = mountSettings(600);
      await renderFrame();
      settings.viewport.dispatchEvent(new Event(event));
      settings.scrollTo(250);
      settings.resize(1800);
      await renderFrame();
      expect(settings.viewport.scrollTop).toBe(250);
      expect(settings.store.scrollPositions[SettingsTab.GENERAL]).toBe(250);
    },
  );

  it("gives explicit section navigation priority, even while content is loading", async () => {
    const store = usePopupStore();
    store.tab = SettingsTab.ROBOT;
    store.scrollPositions[SettingsTab.ROBOT] = 1400;
    store.robotSection = "ultrasonic";
    const settings = mountSettings(600);
    await renderFrame();
    expect(settings.viewport.scrollTop).toBe(0);
    settings.scrollTo(350);
    store.robotSection = undefined;
    settings.resize(1800);
    await renderFrame();
    expect(settings.viewport.scrollTop).toBe(350);

    store.tab = SettingsTab.GENERAL;
    store.scrollPositions[SettingsTab.ROBOT] = 1400;
    settings.resize(600);
    store.tab = SettingsTab.ROBOT;
    await renderFrame();
    store.robotSection = "motion_control";
    settings.scrollTo(400);
    store.robotSection = undefined;
    settings.resize(1800);
    await renderFrame();
    expect(settings.viewport.scrollTop).toBe(400);
  });
});
