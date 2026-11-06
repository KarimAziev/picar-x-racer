import { isUndefined } from "@/util/guards";
import type { ServoConfig, ServoData } from "@/features/settings/stores/robot";

export type ServoName = keyof ServoData;
export const servoNames: ServoName[] = [
  "steering_servo",
  "cam_pan_servo",
  "cam_tilt_servo",
];
export const servoLabels: Record<ServoName, string> = {
  steering_servo: "Steering",
  cam_pan_servo: "Camera pan",
  cam_tilt_servo: "Camera tilt",
};
export const tuningFields = [
  {
    key: "min_angle",
    label: "Minimum angle (°)",
    min: -360,
    max: 360,
    step: 1,
  },
  {
    key: "max_angle",
    label: "Maximum angle (°)",
    min: -360,
    max: 360,
    step: 1,
  },
  { key: "dec_step", label: "Decrease step (°)", max: -1, step: 1 },
  { key: "inc_step", label: "Increase step (°)", min: 1, step: 1 },
  {
    key: "min_pulse",
    label: "Minimum pulse (µs)",
    min: 20,
    max: 2999,
    step: 1,
  },
  {
    key: "max_pulse",
    label: "Maximum pulse (µs)",
    min: 21,
    max: 3000,
    step: 1,
  },
  {
    key: "real_min_angle",
    label: "Angle at minimum pulse (°)",
    min: -360,
    max: 360,
    step: 0.1,
  },
  {
    key: "real_max_angle",
    label: "Angle at maximum pulse (°)",
    min: -360,
    max: 360,
    step: 0.1,
  },
] satisfies Array<{
  key: keyof ServoConfig;
  label: string;
  min?: number;
  max?: number;
  step: number;
}>;
export type NumericTuningField = (typeof tuningFields)[number]["key"];
export type ServoTuning = Pick<ServoConfig, NumericTuningField | "reverse">;
export const getServoTuning = (config: ServoConfig): ServoTuning => ({
  reverse: config.reverse,
  min_angle: config.min_angle,
  max_angle: config.max_angle,
  inc_step: config.inc_step,
  dec_step: config.dec_step,
  min_pulse: config.min_pulse,
  max_pulse: config.max_pulse,
  real_min_angle: config.real_min_angle,
  real_max_angle: config.real_max_angle,
});
export const servoTuningError = (settings: ServoTuning): string => {
  if (
    tuningFields.some(({ key, min, max, step }) => {
      const value = settings[key];
      return (
        !Number.isFinite(value) ||
        (step === 1 && !Number.isInteger(value)) ||
        (!isUndefined(min) && value < min) ||
        (!isUndefined(max) && value > max)
      );
    })
  )
    return "Enter valid values within the indicated ranges.";
  if (settings.min_angle > settings.max_angle)
    return "Minimum angle must not exceed maximum angle.";
  if (settings.min_pulse >= settings.max_pulse)
    return "Minimum pulse must be less than maximum pulse.";
  if (settings.real_min_angle >= settings.real_max_angle)
    return "Angle at minimum pulse must be less than angle at maximum pulse.";
  return "";
};
