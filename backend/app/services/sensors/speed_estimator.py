from __future__ import annotations

import math
from typing import List, Optional

from app.core.px_logger import Logger
from app.util.speed import max_speed_loaded_kmh


class SpeedEstimator:
    """
    Kalman-based ground-speed estimator.

    State vector:
        x = [distance_cm,
             velocity_cm_s]

    Motion model (constant velocity):
        distance_k = distance_{k-1} + velocity_{k-1} * dt + w_d
        velocity_k = velocity_{k-1}                    + w_v

    Only the distance is directly measured by the ultrasonic
    sensor, hence H = [1  0].

    All matrix math is done manually (2×2) to avoid external deps.
    """

    def __init__(
        self,
        *,
        # parameters for theoretical max-speed check, see `max_speed_loaded_kmh`
        mass_kg: float = 0.9,
        wheel_diameter_mm: float = 65,
        stall_torque_kgcm: float = 0.8,
        wheel_rpm_nominal: float = 170,
        supply_voltage: float = 6.0,
        ref_voltage: float = 3.6,
        n_motors: int = 2,
        c_rr: float = 0.02,
        # Kalman noise defaults
        sigma_position_cm: float = 2.0,  # sensor  σ  (≈ 20 mm)
        sigma_speed_cm_s: float = 10.0,  # process σ for speed
        idle_threshold_cm_s: float = 5.0,
    ) -> None:
        self.log = Logger(__name__)

        # -------- maximum physically achievable speed (for sanity gate)
        max_kmh = max_speed_loaded_kmh(
            mass_kg=mass_kg,
            wheel_diameter_mm=wheel_diameter_mm,
            stall_torque_kgcm=stall_torque_kgcm,
            rpm_no_load_ref=wheel_rpm_nominal,
            voltage=supply_voltage,
            ref_voltage=ref_voltage,
            n_motors=n_motors,
            c_rr=c_rr,
        )
        #  +20 %
        self._max_speed_cm_s_physical = max_kmh / 3.6 * 100 * 1.2
        self._idle_threshold_cm_s = idle_threshold_cm_s
        self.log.info(
            "Max speed physical %.1fkm/h, with +20 percents %.1fcm/s",
            max_kmh,
            self._max_speed_cm_s_physical,
        )

        # -------- Kalman matrices (will be scaled per-step)
        self._Q_base = [
            [sigma_position_cm**2, 0.0],
            [0.0, sigma_speed_cm_s**2],
        ]
        self._R_base = sigma_position_cm**2

        # -------- dynamic state (None until first measurement)
        self._x: Optional[List[float]] = None  # [pos, vel]
        self._P: Optional[List[List[float]]] = None  # 2×2 covariance
        self._dt_prev: Optional[float] = None

    @staticmethod
    def _mat_add(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        return [
            [a[0][0] + b[0][0], a[0][1] + b[0][1]],
            [a[1][0] + b[1][0], a[1][1] + b[1][1]],
        ]

    @staticmethod
    def _mat_mul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        return [
            [
                a[0][0] * b[0][0] + a[0][1] * b[1][0],
                a[0][0] * b[0][1] + a[0][1] * b[1][1],
            ],
            [
                a[1][0] * b[0][0] + a[1][1] * b[1][0],
                a[1][0] * b[0][1] + a[1][1] * b[1][1],
            ],
        ]

    @staticmethod
    def _mat_vec_mul(a: List[List[float]], v: List[float]) -> List[float]:
        return [
            a[0][0] * v[0] + a[0][1] * v[1],
            a[1][0] * v[0] + a[1][1] * v[1],
        ]

    @staticmethod
    def _transpose(a: List[List[float]]) -> List[List[float]]:
        return [[a[0][0], a[1][0]], [a[0][1], a[1][1]]]

    def reset(self) -> None:
        """Clear Kalman state - call when the sensor stops/resets."""
        self._x = None
        self._P = None
        self._dt_prev = None

    def process_distance(
        self,
        current_distance: float,
        interval: float,
        *,
        relative_speed: int,
    ) -> Optional[float]:
        """
        Update estimator with a new ultrasonic reading.

        Parameters
        ----------
        current_distance : float
            Raw HC-SR04 measurement in **cm** (-1/-2 means invalid).
        interval : float
            Elapsed time since previous measurement, in **seconds**.
        relative_speed : int
            User-commanded throttle 0-100 %. Used only for plausibility checks.

        Returns
        -------
        Optional[float]
            Estimated speed in **km/h**, truncated to one decimal
            (None if not enough data or reading invalid).
        """
        # ------------- discard unusable values
        if current_distance in (-1, -2) or not 0.0 < current_distance < 600.0:
            self.log.debug("Invalid distance: %.2f cm - skipped.", current_distance)
            return None
        if interval <= 0:
            self.log.warning("Non-positive dt %.4fs - skipped.", interval)
            return None

        if self._x is None:
            self._x = [current_distance, 0.0]
            self._P = [
                [self._R_base, 0.0],
                [0.0, 500.0],  # very uncertain velocity
            ]
            self._dt_prev = interval
            return None  # need at least 2 points

        assert self._P is not None
        dt = interval

        # predict
        F = [[1.0, dt], [0.0, 1.0]]

        x_pred = self._mat_vec_mul(F, self._x)

        # scale process noise with dt
        Q = [
            [self._Q_base[0][0] * dt * dt, 0.0],
            [0.0, self._Q_base[1][1] * dt],
        ]
        P_pred = self._mat_add(
            self._mat_mul(self._mat_mul(F, self._P), self._transpose(F)),
            Q,
        )

        z = current_distance
        H = [1.0, 0.0]

        y = z - (H[0] * x_pred[0] + H[1] * x_pred[1])  # innovation

        R = self._measurement_variance_cm2(relative_speed)
        S = P_pred[0][0] + R  # scalar
        K0 = P_pred[0][0] / S  # Kalman gain (position row)
        K1 = P_pred[1][0] / S  # Kalman gain (velocity row)

        self._x = [
            x_pred[0] + K0 * y,
            x_pred[1] + K1 * y,
        ]

        # covariance update (I - K H) P
        KH00 = K0 * H[0]
        KH10 = K1 * H[0]
        self._P = [
            [(1 - KH00) * P_pred[0][0], (1 - KH00) * P_pred[0][1]],
            [-KH10 * P_pred[0][0] + P_pred[1][0], -KH10 * P_pred[0][1] + P_pred[1][1]],
        ]

        speed_cm_s = abs(self._x[1])

        commanded_cm_s = (relative_speed / 100.0) * self._max_speed_cm_s_physical

        # ---------------------------------------------------------------- 0) Idle-gate
        if commanded_cm_s == 0.0 and speed_cm_s < self._idle_threshold_cm_s:
            speed_cm_s = 0.0

        if speed_cm_s > self._max_speed_cm_s_physical:
            self.log.debug(
                "Speed %.1f cm/s above physical limit %.1f cm/s → clamped.",
                speed_cm_s,
                self._max_speed_cm_s_physical,
            )
            speed_cm_s = self._max_speed_cm_s_physical

        if commanded_cm_s > self._idle_threshold_cm_s:
            if abs(speed_cm_s - commanded_cm_s) > 0.4 * commanded_cm_s:
                self.log.debug(
                    "Speed %.1f cm/s deviates from command %.1f cm/s → blended.",
                    speed_cm_s,
                    commanded_cm_s,
                )
                speed_cm_s = 0.5 * speed_cm_s + 0.5 * commanded_cm_s

        speed_kmh = speed_cm_s * 0.036
        final_result = math.trunc(speed_kmh * 10) / 10.0
        self.log.debug(
            "Final estimated speed=%skm/h, relative_speed=%s, interval=%s",
            final_result,
            relative_speed,
            interval,
        )

        return final_result

    def _measurement_variance_cm2(self, relative_speed: int) -> float:
        """
        Inflate measurement noise with motor RPM (simple heuristic):
        +3 % variance per 1 % throttle.
        """
        factor = 1.0 + 0.03 * max(0, min(relative_speed, 100))
        return self._R_base * factor * factor
