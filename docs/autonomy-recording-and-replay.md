# Autonomy recording and replay

## Mission routes

The mission panel reads `/px/api/autonomy/navigation/mission/runtime`, which
returns mission progress, navigation execution, and the current live route in
one event-loop snapshot. Polls do not overlap. Polling continues after a mission
finishes so the canvas receives the cleared route.

Yellow and magenta lines show reviewed forward and reverse preflight paths.
The cyan line is the current live route; dashed cyan sections represent reverse
travel. Every target visit is planned from fresh fused localization. A new leg
clears the previous route before planning. Map revisions invalidate route
overlays. Operator-action errors remain visible across successful runtime polls.

## Record a drive

1. Configure the robot or simulator and reset its pose if needed.
2. Open the autonomy workspace and select **Start recording**.
3. Map, drive, or execute a mission normally.
4. Select **Stop recording**, then **Download session**.

Recording observes the existing topic bus and never starts movement. The
backend retains files in `autonomy-recordings/` beside its `config.json`.
Each session uses a unique ID and creates a new file; starting another recording
does not overwrite previous sessions. The current panel offers the latest file;
older files remain in that directory.

The API endpoints are:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/px/api/autonomy/recordings/status` | Current recording state and counters |
| POST | `/px/api/autonomy/recordings/start` | Start a session |
| POST | `/px/api/autonomy/recordings/stop` | Drain and close the session |
| GET | `/px/api/autonomy/recordings/{session_id}/download` | Download a closed session |

The version-1 JSONL format contains a header, ordered events, and a footer.
The header includes relevant hardware/autonomy configuration at recording start,
the robot-hat version, Git commit, and whether tracked source files were dirty.
Camera, network, and other unrelated settings are excluded. Keep configuration
fixed during a recording; changes to configuration are not currently captured.

Events include encoder readings, IMU, LiDAR, steering feedback, odometry, fused
pose, pose corrections, resolved actuator commands, directional safety,
simulated truth, occupancy maps, mission status transitions, and live navigation
plans. Existing retained messages are marked `snapshot: true`. Each event stores
the original payload timestamps as well as its publication-observation timestamp
and a session sequence number.
LiDAR no-return distances (positive infinity) are encoded as JSON `null` and
restored to infinity during replay.

Disk serialization runs in a worker thread. The observer queue is bounded to
2,048 events. Overflow drops the oldest queued observations and increments the
visible dropped-event counter; it does not stall control or other subscribers.
Files are limited to approximately 256 MiB each (the footer can add a few bytes).
Reaching the limit or encountering an I/O error stops recording and reports an
error. No automatic deletion or disk-retention policy is configured.

## Replay offline

From the repository root:

```sh
cd backend
.venv/bin/python -m app.services.autonomy.replay /absolute/path/to/session.jsonl
```

By default replay runs without wall-clock delays. To inspect playback at its
recorded pace, add `--speed 1`; `--speed 2` uses double speed. Output is a JSON
report of topic counts, recording gaps/errors, the last recorded fused pose,
and the pose recomputed from recorded odometry, IMU, and correction observations.

Playback creates a private topic bus and explicit replay clock. It never obtains
the application's live bus or creates hardware controllers. Recorded motor
commands remain diagnostic observations. No command is sent to the vehicle.
For tests and debugging, `SessionReplay.step()` advances one event on an asyncio
event loop; call `close()` afterward to release the file.

The reader validates format version, event sequence, timestamps, message types,
and the closing event count. A truncated recording or missing footer fails
explicitly. A closed recording with dropped events or a recorder error can still
be inspected, and those limitations are included in the report.

## What replay currently measures

This is deterministic event playback and a fresh evaluation of the pure pose
estimator. It does not restore the original estimator's internal state, rerun
the complete navigation stack, or reproduce asynchronous scheduling from the
original drive. A recording begun mid-drive can therefore produce a recomputed
pose different from the recorded fused pose without indicating a regression.

Start a new session after a simulator/odometry reset. Sequence resets inside a
file are currently rejected by the estimator, rather than silently joined into
one trajectory. Full estimator checkpoints, reset events, configuration-change
events, and recomputation of raw-encoder odometry are future extensions.

## Next milestones

- [Fixed-step sensor-fault regressions](autonomy-simulation-fault-tests.md) now
  cover delayed/missing inputs, safe navigation failure, and explicit restart.
- Use recorded scenarios to test delayed or missing sensors and mission recovery.
- Validate [observed-map localization](observed-map-localization.md) on recorded
  and real drives; the known-world matcher remains a simulation reference.
- Extend to map correction/loop closure after frozen-map localization is validated.
- Add guided gyro, steering, and drivetrain-distance calibration exercises.
