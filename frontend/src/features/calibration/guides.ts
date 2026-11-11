import type { CalibrationKind, Trial } from "./session";
export type GuideKind = CalibrationKind | "body" | "mounting";
export const guides: {
  kind: GuideKind;
  title: string;
  description: string;
  steps: string[];
}[] = [
  {
    kind: "body",
    title: "Body measurements",
    description: "Measure axle spacing and the space the robot occupies.",
    steps: [
      "Place the robot on a level surface. Use a ruler or tape measure; centimetres are fine.",
      "Measure between the centres of the front and rear axles. Then measure the body including wheels and attached equipment.",
      "Review the measurements before saving. These describe the robot's size; they do not start movement.",
    ],
  },
  {
    kind: "mounting",
    title: "Sensor mounting",
    description: "Tell the robot where its LiDAR and IMU are mounted.",
    steps: [
      "Use the midpoint of the rear axle as your reference. Face the same direction as the robot.",
      "Measure the sensor's forward, left and vertical offsets from that reference. Enter negative values for backward or right offsets.",
      "Check the sensor's marked axes against the robot's axes. A level, forward-facing sensor has 0° rotation on all three axes.",
    ],
  },
  {
    kind: "steering_center",
    title: "Straighten the wheels",
    description: "Adjust steering until the front wheels point straight ahead.",
    steps: [
      "Enable the steering servo and its physical position sensor in Advanced settings. Raise the front wheels off the floor and keep fingers clear of the linkage.",
      "Start the trial, then adjust Steering command (°) in small steps until both front wheels point along the chassis.",
      "Wait one second with the wheels steady, record the position, then review and apply it as the straight-ahead position.",
    ],
  },
  {
    kind: "steering_range",
    title: "Steering angles",
    description: "Match sensor readings to actual wheel angles.",
    steps: [
      "Complete Straighten the wheels first. Use a protractor or printed angle guide. Raise the front wheels and keep clear of the linkage.",
      "Start a trial and adjust the steering. Measure the average direction of the two front wheels relative to the chassis: left is negative, right is positive.",
      "Record separate straight, left and right trials. Select at least three positions to review the steering table.",
    ],
  },
  {
    kind: "wheel_distance",
    title: "Encoder distance calibration",
    description: "Roll the robot over a measured distance to calibrate how encoder counts translate into travel distance.",
    steps: [
      "Enable physical drive encoders in Advanced settings. Mark a straight path of 50–100 cm on a level floor and measure the distance between the marks. Align the rear axle with the first mark before starting.",
      "Recording is active. Gently roll the robot forward with its wheels straight until the rear axle reaches the second mark. Do not lift or drag it.",
      "Record the trial at the second mark. Repeat at least twice; the system checks that the measurements agree within 5%.",
    ],
  },
  {
    kind: "imu_bias",
    title: "Stationary rotation sensor",
    description: "Measure the IMU's reading while the robot is still.",
    steps: [
      "Enable the physical IMU in Advanced settings. Place the robot on a firm, level surface and let it settle.",
      "Start recording. Do not touch the robot for at least 4 seconds.",
      "Record two trials and review the measured offset. The system checks that the readings stayed steady.",
    ],
  },
  {
    kind: "speed",
    title: "Driving speed",
    description: "Measure real speed at several motor power levels.",
    steps: [
      "Enable physical LiDAR and drive encoders, a motor and the steering servo. Complete straight-wheel calibration. Face a broad, flat wall and clear the driving path. A camera or detection model is not required.",
      "Hold Drive for at least 2 seconds while the wheels stay straight, then release to stop. Wait one second before recording. Stop well before the boundary. For reverse trials, keep facing the wall and clear the space behind the robot too.",
      "Compare the accepted trials below. Repeat twice at each power level, at two or more levels in both directions. Start low; successful trials unlock steps of up to 10% power. Review the selected trials to see the speeds that will be saved.",
    ],
  },
  {
    kind: "stopping",
    title: "Stopping distance",
    description: "Measure how far the robot rolls after you release Drive.",
    steps: [
      "Complete Body measurements and Driving speed first. Face a flat wall, clear the driving path, and select the highest calibrated power for this direction. Use the same floor and load you expect to drive with.",
      "Hold Drive for at least 2 seconds until speed is steady, then release and wait one second before recording. Never use the wall as a physical stop.",
      "Record at least two trials at the highest calibrated speed in each direction. Review the proposed safety distances; the system includes the body and a response margin.",
    ],
  },
];
export function trialSummary(trial: Trial): string {
  if (!trial.accepted) return trial.reason;
  if (trial.mean_speed_mps !== null)
    return `${trial.direction}, ${trial.power_percent}% power: ${trial.mean_speed_mps.toFixed(3)} m/s (observed ${trial.minimum_speed_mps?.toFixed(3)}–${trial.maximum_speed_mps?.toFixed(3)} m/s)${trial.kind === "stopping" ? `; stop travel ${((trial.stopping_distance_m ?? 0) * 100).toFixed(1)} cm` : ""}`;
  if (trial.distance_per_tick_m !== null)
    return `${((trial.distance_m ?? 0) * 100).toFixed(1)} cm travelled; ${(trial.distance_per_tick_m * 1000).toFixed(5)} mm per encoder count`;
  if (trial.gyro_bias_radps !== null)
    return `Stationary offset: ${trial.gyro_bias_radps.toFixed(5)} rad/s`;
  return `Wheel position: ${trial.steering_degrees?.toFixed(1)}°; sensor: ${trial.sensor_angle_deg?.toFixed(1)}°`;
}
/** Human-readable review text uses the same values that will be persisted. */
export function reviewLines(update: Record<string, any>): string[] {
  const lines: string[] = [];
  if (update.ackermann_odometry?.wheel_radius_m)
    lines.push(
      `Effective wheel radius: ${(update.ackermann_odometry.wheel_radius_m * 100).toFixed(3)} cm (calculated from travel)`,
    );
  if (update.pose_estimation)
    lines.push(
      `Stationary rotation offset: ${update.pose_estimation.imu_yaw_bias_radps.toFixed(5)} rad/s`,
    );
  for (const direction of ["forward", "reverse"]) {
    for (const point of update.motion_control?.[`${direction}_speed_curve`] ??
      [])
      lines.push(
        `${direction}: ${point.power_percent}% motor power → ${point.speed_mps.toFixed(3)} m/s`,
      );
  }
  if (update.steering_servo)
    lines.push(
      `Straight-ahead servo adjustment: ${update.steering_servo.calibration_offset.toFixed(1)}°`,
    );
  const steering = update.localization_sensors?.steering;
  if (steering?.invert_direction !== undefined)
    lines.push(
      `Steering sensor direction: ${steering.invert_direction ? "reversed" : "normal"} (determined from your measurements)`,
    );
  if (steering?.center_angle_deg !== undefined)
    lines.push(
      `Straight-ahead sensor position: ${steering.center_angle_deg.toFixed(1)}°`,
    );
  for (const point of steering?.calibration_points ?? [])
    lines.push(
      `Sensor offset ${point.sensor_offset_deg.toFixed(1)}° → wheel angle ${((point.wheel_angle_rad * 180) / Math.PI).toFixed(1)}°`,
    );
  if (update.lidar_safety)
    lines.push(
      `Stop boundary: ${(update.lidar_safety.stop_distance_m * 100).toFixed(1)} cm from the rear axle`,
      `Slow-down boundary: ${(update.lidar_safety.slow_distance_m * 100).toFixed(1)} cm from the rear axle`,
    );
  return lines;
}
