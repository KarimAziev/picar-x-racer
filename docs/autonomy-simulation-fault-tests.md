# Repeatable autonomy sensor-fault tests

These regressions exercise the existing fixed-step Ackermann simulator,
wheel/IMU estimators, frozen-map matcher, navigation planner/executor, and motion
arbiter without constructing hardware controllers or accessing the live app bus.
They require no robot, browser, robot-hat changes, or configuration migration.

## Run

From the repository root:

```sh
cd backend
.venv/bin/python -m unittest -v \
  tests.services.autonomy.test_sensor_fault_scenarios \
  tests.services.autonomy.test_navigation_fault_scenarios \
  tests.services.autonomy.test_lidar_safety \
  tests.services.autonomy.test_odometry
```

All tests are also included in normal `unittest discover` and `make check`.

## Scenarios and acceptance criteria

| Scenario | Required result |
| --- | --- |
| Ideal straight, left-arc, and right-arc driving | Final position agrees with simulated truth within 2 mm in these calibrated fixtures. |
| Seeded sensor imperfections plus delivery faults | Repeated runs produce identical reports; final position error stays below 10 cm for this fixture. |
| IMU loss or 300 ms latency | Stale IMU data is rejected, estimation falls back to wheels, and wheel/IMU fusion resumes with fresh data. |
| Thirty lost encoder messages during straight driving | Cumulative counts retain the missing distance; final error stays below 2 mm. |
| Missing steering feedback or delayed encoders | Odometry rejects stale/future steering associations and resumes when valid inputs return. |
| LiDAR outage or a stream of delayed scans | The real arbiter resolves a stop while scan measurements are stale; fresh scans can remove the LiDAR constraint. |
| Future or out-of-order clear LiDAR scans | They cannot remove an obstacle/safety block. |
| Delayed frozen-map correction | The estimator rejects the old correction; a subsequent fresh scan match can correct the pose. |
| Navigation with a 100 ms encoder gap or an IMU outage | The reviewed route can complete. |
| Navigation with an 800 ms encoder outage | Execution fails on stale localization at the first 20 ms scenario tick beyond its 500 ms deadline, revokes autonomy, and resolves zero speed. |
| Sensors recover after failed navigation | The vehicle stays disarmed. A new reviewed and explicitly started route can run. |

These thresholds are regression expectations for specific synthetic geometry,
timing, and sensor settings—not hardware accuracy guarantees.

## Test architecture

`backend/tests/services/autonomy/fault_scenarios.py` contains the test-only
delivery scheduler. `DeliveryFault` selects a sensor topic and a half-open range
of acquisition steps, then drops messages or delays their delivery by a fixed
number of steps. Each step represents 20 ms. Queued messages retain their
original acquisition timestamps and cumulative encoder ticks. Equal delivery
times preserve capture order; pending events and the source observer are bounded.

The simulator publishes onto a private source bus. Only encoder, steering, IMU,
and LiDAR messages cross into a second private measurement bus. Ground truth is
used for scoring only; commands and truth are not delivered as sensor input.
Existing independent seeded simulator noise streams provide repeatability.

Drive scenarios call the production odometry and pose-estimator update methods
explicitly. LiDAR scenarios use the service's scan-processing and measurement
watchdog methods and resolve its constraints through the real arbiter. Separate
async tests cover the service's subscription and arrival-timeout path.

Navigation scenarios replay the simulated fused-pose timeline into the real
planner and asynchronous executor with an injected `ReplayClock`; their
hardware-free motion facade uses the real arbiter. Zero-duration event-loop
yields run the executor without waiting for scenario time to elapse. In normal
runtime, planning and execution still default to `SystemClock`.

These are **not a complete closed-loop mission simulation**: the navigation
tests follow a precomputed simulated pose stream instead of feeding each
navigation output back into the plant. Multi-leg mission recovery, dynamic
obstacles, full transport scheduling, and Raspberry Pi timing remain follow-ups.
JSONL recording/replay is unchanged; these tests do not mutate recorded files.

## Runtime fixes exposed by the tests

### LiDAR freshness is based on measurement time

Receiving an old clear scan used to clear the safety constraint even when its
measurement was already stale. Safety now rejects stale, future, and
non-increasing scan timestamps. A delayed but still valid scan receives only
the remaining part of its measurement lifetime before the watchdog blocks.
The independent no-arrival timeout remains fail-closed.

### Odometry uses cumulative counts between consumed samples

Publisher `delta_ticks` values cover only the preceding acquired sample. They
cannot cover messages a consumer missed. The estimator now differences
cumulative counters between accepted samples for individual wheels or the
rear-drivetrain-average encoder. A first sample establishes a baseline without
inventing motion. Changing encoder layout requires an odometry reset.

This recovers traveled distance across missed messages, but cannot reconstruct
steering changes or slip during an unobserved interval. The recovered pose can
still be approximate; navigation's stale-pose stop remains necessary. An
unannounced hardware counter reset is also not distinguishable from signed
movement: reset/reconfigure the estimator when resetting encoder counters.

## Next extensions

- Feed navigation output back into the simulator for closed-loop multi-target
  missions with faults, pauses, and recovery.
- Evaluate delayed scans during motion and map ambiguity with recorded C1 data.
- Add calibration exercises and hardware-specific timing/accuracy bounds.
