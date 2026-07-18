// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useStore } from "@/features/settings/stores/battery";

describe("battery store metrics", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("merges partial battery broadcasts by name", () => {
    const store = useStore();
    store.mergeBatteryMetrics([
      {
        name: "Main battery",
        voltage: 8.1,
        current: 1.2,
        percentage: 87.5,
        error: null,
      },
    ]);
    store.mergeBatteryMetrics([
      {
        name: "Servo supply",
        voltage: 5.4,
        current: null,
        percentage: 70,
        error: null,
      },
    ]);

    expect(store.batteries).toHaveLength(2);
    expect(store.batteries[0].current).toBe(1.2);
    expect(store.batteries[1].current).toBeNull();
  });

  it("replaces metrics for an existing battery", () => {
    const store = useStore();
    store.mergeBatteryMetrics([
      {
        name: "Main battery",
        voltage: 8.1,
        current: null,
        percentage: 87.5,
        error: null,
      },
    ]);
    store.mergeBatteryMetrics([
      {
        name: "Main battery",
        voltage: null,
        current: null,
        percentage: null,
        error: "I2C failure",
      },
    ]);

    expect(store.batteries).toEqual([
      {
        name: "Main battery",
        voltage: null,
        current: null,
        percentage: null,
        error: "I2C failure",
      },
    ]);
  });
});
