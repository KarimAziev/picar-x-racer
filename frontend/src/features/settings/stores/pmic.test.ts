// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { AxiosRequestConfig } from "axios";
import { usePmicStore, type PmicStatus } from "./pmic";
import { useStore as useSettingsStore } from "./settings";

const get = vi.hoisted(() =>
  vi.fn<(path: string, config?: AxiosRequestConfig) => Promise<PmicStatus>>(),
);
const post = vi.hoisted(() => vi.fn());
vi.mock("@/api", () => ({ appApi: { get, post } }));
const sample: PmicStatus = {
  readings: [
    { name: "3V3_SYS_V", value: 3.302609, unit: "V" },
    { name: "3V3_SYS_A", value: 0.1903064, unit: "A" },
    { name: "EXT5V_V", value: 4.86822, unit: "V" },
  ],
  measured_at: "2026-11-04T10:00:00+00:00",
  error: null,
};

beforeEach(() => {
  localStorage.clear();
  setActivePinia(createPinia());
  vi.useFakeTimers();
  get.mockReset().mockResolvedValue(sample);
  post.mockReset().mockResolvedValue({});
});
afterEach(() => {
  usePmicStore().stopPolling();
  vi.useRealTimers();
});

describe("PMIC monitor", () => {
  it("saves PMIC preferences through user settings", async () => {
    const store = usePmicStore();
    const settings = useSettingsStore();
    expect(store.channels).toEqual(["3V3_SYS_V", "3V3_SYS_A"]);
    expect(store.intervalMs).toBe(5000);
    store.selectedChannels = ["EXT5V_V"];
    store.refreshSeconds = 10;
    store.enabled = false;
    const expected = {
      enabled: false,
      selected_channels: ["EXT5V_V"],
      refresh_seconds: 10,
    };
    expect(settings.data.pmic).toEqual(expected);
    expect(settings.generalSettings.pmic).toEqual(expected);
    await store.savePreferences();
    expect(post).toHaveBeenCalledWith("/api/settings", { pmic: expected });
    expect(localStorage.getItem("pinia/pmic/channels")).toBeNull();
    expect(localStorage.getItem("pinia/pmic/interval")).toBeNull();
    expect(localStorage.getItem("pinia/pmic/enabled")).toBeNull();
  });

  it("follows settings loaded or synchronized from the server", () => {
    const store = usePmicStore();
    const settings = useSettingsStore();
    settings.data = {
      ...settings.data,
      pmic: {
        enabled: false,
        selected_channels: ["EXT5V_V"],
        refresh_seconds: 20,
      },
    };
    expect(store.enabled).toBe(false);
    expect(store.channels).toEqual(["EXT5V_V"]);
    expect(store.intervalMs).toBe(20000);
    setActivePinia(createPinia());
    expect(usePmicStore().channels).toEqual(["3V3_SYS_V", "3V3_SYS_A"]);
  });

  it("clamps invalid intervals and preserves missing selected channels", async () => {
    const store = usePmicStore();
    store.refreshSeconds = 0;
    expect(store.intervalMs).toBe(1000);
    store.refreshSeconds = 1000;
    expect(store.intervalMs).toBe(300000);
    store.refreshSeconds = NaN;
    expect(store.intervalMs).toBe(5000);
    store.selectedChannels = ["BATT_V"];
    await store.refresh();
    expect(store.selectedReadings).toEqual([
      { name: "BATT_V", reading: undefined },
    ]);
  });

  it("polls at the configured interval and stops cleanly", async () => {
    const store = usePmicStore();
    store.refreshSeconds = 2;
    store.startPolling();
    await vi.advanceTimersByTimeAsync(1999);
    expect(get).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(get).toHaveBeenCalledTimes(2);
    store.stopPolling();
    await vi.advanceTimersByTimeAsync(10000);
    expect(get).toHaveBeenCalledTimes(2);
  });

  it("does not overlap slow reads and discards results after stopping", async () => {
    let resolveRequest!: (value: PmicStatus) => void;
    get.mockImplementation(
      () =>
        new Promise<PmicStatus>((resolve) => {
          resolveRequest = resolve;
        }),
    );
    const store = usePmicStore();
    store.startPolling();
    await store.refresh();
    await vi.advanceTimersByTimeAsync(10000);
    expect(get).toHaveBeenCalledTimes(1);
    const signal = get.mock.calls[0]?.[1]?.signal;
    store.stopPolling();
    expect(signal?.aborted).toBe(true);
    resolveRequest(sample);
    await vi.advanceTimersByTimeAsync(10000);
    expect(store.readings).toEqual([]);
    expect(store.loading).toBe(false);
    expect(get).toHaveBeenCalledTimes(1);
  });

  it("clears stale measurements on a failed read and recovers", async () => {
    const store = usePmicStore();
    await store.refresh();
    expect(store.readings).toHaveLength(3);
    get.mockRejectedValueOnce(new Error("Offline"));
    await store.refresh();
    expect(store.readings).toEqual([]);
    expect(store.measuredAt).toBeNull();
    expect(store.error).toBeTruthy();
    await store.refresh();
    expect(store.error).toBeNull();
    expect(store.readings).toHaveLength(3);
  });

  it("reports unsupported hardware without inventing readings", async () => {
    get.mockResolvedValueOnce({
      readings: [],
      measured_at: null,
      error: "Not supported",
    });
    const store = usePmicStore();
    await store.refresh();
    expect(store.error).toBe("Not supported");
    expect(
      store.selectedReadings.every((item) => item.reading === undefined),
    ).toBe(true);
  });
});
