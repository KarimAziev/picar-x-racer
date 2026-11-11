// @vitest-environment jsdom
import { createPinia } from "pinia";
import { toRaw } from "vue";
import { describe, expect, it } from "vitest";
import { useRobotStore } from "@/features/settings/stores";
import { guideProgress } from "@/features/calibration/progress";

const config = () => structuredClone(toRaw(useRobotStore(createPinia()).data));
describe("saved calibration progress", () => {
  it("does not mistake imported geometry or a default zero bias for reviewed measurements", () => {
    const data = config();
    data.navigation.body_length_m = 0.42;
    expect(guideProgress(data, "body").state).toBe("review");
    expect(guideProgress(data, "imu_bias").state).toBe("todo");
    expect(guideProgress(data, "mounting").state).toBe("review");
  });
  it("recognizes a reviewed zero bias after configuration round-trip and invalidates changed settings", () => {
    const data = config();
    data.calibration_progress = {
      imu_bias: { "pose_estimation.imu_yaw_bias_radps": 0 },
    };
    expect(guideProgress(structuredClone(data), "imu_bias").state).toBe(
      "complete",
    );
    data.navigation.body_width_m = 0.22;
    expect(guideProgress(data, "imu_bias").state).toBe("complete");
    data.pose_estimation.imu_yaw_bias_radps = 0.01;
    expect(guideProgress(data, "imu_bias").detail).toContain(
      "Settings changed",
    );
  });
  it("tracks both mounting measurements independently, including a valid all-zero transform", () => {
    const data = config();
    data.calibration_progress = {
      lidar_mount: {
        "localization_sensors.lidar.transform": {
          ...data.localization_sensors.lidar.transform,
        },
      },
    };
    expect(guideProgress(data, "mounting").label).toBe("1 of 2 completed");
    data.calibration_progress.imu_mount = {
      "localization_sensors.imu.transform": {
        ...data.localization_sensors.imu.transform,
      },
    };
    expect(guideProgress(data, "mounting").state).toBe("complete");
    data.localization_sensors.imu.transform.yaw_rad = -Math.PI / 2;
    expect(guideProgress(data, "mounting").state).toBe("partial");
    expect(guideProgress(data, "mounting").detail).toContain(
      "IMU: needs review",
    );
  });
  it("detects changes to calibration tables and ignores object key order", () => {
    const data = config();
    data.motion_control.forward_speed_curve = [
      { power_percent: 20, speed_mps: 0.1 },
    ];
    data.calibration_progress = {
      speed: {
        "motion_control.forward_speed_curve": [
          { speed_mps: 0.1, power_percent: 20 },
        ],
      },
    };
    expect(guideProgress(data, "speed").state).toBe("complete");
    data.motion_control.forward_speed_curve.push({
      power_percent: 30,
      speed_mps: 0.2,
    });
    expect(guideProgress(data, "speed").state).toBe("review");
  });
});
