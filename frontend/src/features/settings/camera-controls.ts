import { isNil, isNumber } from "@/util/guards";

export type CameraControlMode = "auto" | "manual";

export interface CameraControls {
  exposure_mode?: CameraControlMode | null;
  exposure_time_us?: number | null;
  focus_mode?: CameraControlMode | null;
  focus_position?: number | null;
}

export interface CameraControlRange {
  min: number;
  max: number;
  step?: number | null;
  unit: string;
}

export interface CameraControlCapabilities {
  exposure_modes: CameraControlMode[];
  exposure_time_us?: CameraControlRange | null;
  focus_modes: CameraControlMode[];
  focus_position?: CameraControlRange | null;
  message?: string | null;
}

export const validCameraControls = (
  controls: CameraControls,
  capabilities?: CameraControlCapabilities,
  fps?: number | null,
) => {
  const valid = (
    mode: CameraControlMode | null | undefined,
    value: number | null | undefined,
    modes: CameraControlMode[],
    range?: CameraControlRange | null,
  ) => {
    if (isNil(mode)) return isNil(value);
    if (!modes.includes(mode)) return false;
    if (mode === "auto") return isNil(value);
    if (!isNumber(value) || !Number.isFinite(value) || !range) return false;
    if (value < range.min || value > range.max) return false;
    const steps = range.step ? (value - range.min) / range.step : 0;
    return Math.abs(steps - Math.round(steps)) < 1e-6;
  };
  const exposure = controls.exposure_time_us;
  return (
    valid(
      controls.exposure_mode,
      exposure,
      capabilities?.exposure_modes ?? [],
      capabilities?.exposure_time_us,
    ) &&
    valid(
      controls.focus_mode,
      controls.focus_position,
      capabilities?.focus_modes ?? [],
      capabilities?.focus_position,
    ) &&
    (isNil(exposure) ||
      (Number.isInteger(exposure) &&
        exposure > 0 &&
        exposure <= 1_000_000 &&
        (!fps || exposure <= 1_000_000 / fps)))
  );
};
