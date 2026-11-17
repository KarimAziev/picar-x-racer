import { describe, expect, it } from "vitest";
import {
  validCameraControls,
  type CameraControlCapabilities,
} from "@/features/settings/camera-controls";

const capabilities: CameraControlCapabilities = {
  exposure_modes: ["auto", "manual"],
  exposure_time_us: { min: 100, max: 100000, step: 100, unit: "µs" },
  focus_modes: ["auto", "manual"],
  focus_position: { min: 0, max: 10, unit: "dioptres" },
};

describe("camera control validation", () => {
  it("allows camera defaults without adjustable controls", () => {
    expect(validCameraControls({})).toBe(true);
    expect(validCameraControls({ focus_mode: "auto" })).toBe(false);
  });
  it("requires a manual value and rejects values in automatic mode", () => {
    expect(validCameraControls({ exposure_mode: "manual" }, capabilities)).toBe(
      false,
    );
    expect(
      validCameraControls(
        { exposure_mode: "auto", exposure_time_us: 1000 },
        capabilities,
      ),
    ).toBe(false);
    expect(validCameraControls({ focus_position: 2 }, capabilities)).toBe(
      false,
    );
  });
  it("enforces device ranges, steps and frame intervals", () => {
    expect(
      validCameraControls(
        { exposure_mode: "manual", exposure_time_us: 10000 },
        capabilities,
        30,
      ),
    ).toBe(true);
    expect(
      validCameraControls(
        { exposure_mode: "manual", exposure_time_us: 1050 },
        capabilities,
      ),
    ).toBe(false);
    expect(
      validCameraControls(
        { exposure_mode: "manual", exposure_time_us: 50000 },
        capabilities,
        30,
      ),
    ).toBe(false);
    expect(
      validCameraControls(
        { focus_mode: "manual", focus_position: 11 },
        capabilities,
      ),
    ).toBe(false);
    expect(
      validCameraControls(
        { focus_mode: "manual", focus_position: NaN },
        capabilities,
      ),
    ).toBe(false);
  });
});
