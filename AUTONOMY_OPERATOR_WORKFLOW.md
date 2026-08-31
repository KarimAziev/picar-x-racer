# Autonomy Operator Workflow Specification

Status: active implementation specification

Related architecture: [AUTONOMY_ARCHITECTURE_PLAN.md](./AUTONOMY_ARCHITECTURE_PLAN.md)

## Purpose

This document defines how a user should configure, observe, manually drive, map,
simulate, and eventually autonomously navigate the robot. It complements the
backend-oriented autonomy architecture with a product-level operating model.

The central distinction is:

```text
Settings          configure what hardware exists
Diagnostics       verify hardware, timing, signs, and calibration
Operator workspace drive, map, monitor safety, and run missions
Autonomy backend  produce motion only for an explicit, cancelable user action
```

Sensor availability, map construction, permission to move, and an active
mission are separate concerns. Enabling a sensor or mapping capability must
never, by itself, cause vehicle motion.

## Current Baseline

The application currently has:

- typed LiDAR, IMU, encoder, steering, odometry, safety, and map messages;
- real and mock localization sensor adapters;
- Ackermann odometry based on encoder distance and steering angle;
- a bounded local occupancy grid;
- a mode-aware motion arbiter and single hardware writer;
- LiDAR-derived forward speed constraints;
- browser telemetry, LiDAR preview, and map preview;
- manual keyboard and joystick control;
- a dedicated `/autonomy` operator workspace with camera, map, split, and 3D
  telemetry views;
- explicit local mapping sessions with start/resume, pause, finish, clear, and
  reset operations;
- persistent robot mode, command source/reason, pose, speed, sensor, mapping,
  and safety status in the operator workspace;
- disarmed motion-control startup with explicit manual arming;
- cancelable, odometry-bounded straight-distance and fixed steering-arc actions;
- a hot-reconfigurable coherent Ackermann simulation environment with physical
  drive isolation, synchronized steering/encoder/IMU topics, runtime status,
  and pose reset;
- an older reactive ultrasonic obstacle-avoidance behavior;
- a `/virtual` compatibility redirect to the workspace's Three.js view.

Important current limitations:

- the localization and mapping features do not produce autonomous motion;
- the current occupancy grid is a fixed local odometry grid, not SLAM;
- maps cannot yet be saved, loaded, or localized against;
- the map canvas does not yet visualize bounds warnings or individual scan
  insertion/rejection locations;
- there is no navigation goal, path follower, exploration behavior, or
  autonomy supervisor;
- steering-arc execution currently uses a fixed steering command and validates
  final measured yaw; it is not yet a closed-loop curvature controller;
- high-risk settings and calibration flows do not yet disarm automatically;
- coherent simulation does not yet include a fixed world, collision response,
  or world-aware LiDAR ray casting;
- the Three.js vehicle visualizes commanded gauges and is not an odometry or
  simulation source.

## Product Principles

### Movement is always explicit

The robot moves only after one of these user actions:

- arm manual control and provide a live manual command;
- start a named autonomous action or mission;
- start a calibration operation that explicitly requires motion.

Opening a page, enabling telemetry, enabling mapping, loading a map, or
connecting a sensor does not authorize movement.

### Settings is not a driving surface

The settings popup remains non-drivable. It may show compact health and preview
information, but it is not the place for map operation or missions. Opening
hardware settings should eventually issue a stop and, for high-risk changes,
disarm the robot.

### Modes and missions are different

`RobotMode.AUTONOMOUS` permits autonomy-origin motion intents. It does not
describe which behavior is running. Mission state separately describes an
operation such as exploring, driving a relative arc, or navigating to a goal.

### Visualizations consume robot state

The map and Three.js model consume odometry, steering, scans, paths, and
commanded motion. They never generate authoritative odometry from animation.

### Safety remains outside mission logic

Navigation and manual control submit candidate motion. The motion arbiter and
safety services constrain or stop it. A planner must not bypass the arbiter,
and a UI must not write directly to motors.

## Orthogonal Runtime State

The UI and backend must represent these state dimensions independently:

| Concern | Example states | Meaning |
| --- | --- | --- |
| Sensor acquisition | disabled, starting, running, stale, error | Whether measurements are available |
| Mapping session | idle, mapping, paused, complete, error | Whether synchronized scans are modifying a grid |
| Robot motion mode | disarmed, manual, autonomous, calibration, estop, fault | Which intent source may control hardware |
| Mission | none, preparing, running, blocked, paused, canceling, succeeded, failed | Which long-running behavior is active |
| Localization | unavailable, initializing, tracking, degraded, lost | Whether a map-relative pose is trustworthy |

Examples:

- mapping may run while the robot is manually driven;
- telemetry may run while the robot is disarmed;
- a map may be loaded while localization is still unavailable;
- the robot may be in autonomous mode with a blocked mission and therefore
  command zero speed;
- emergency stop cancels permission to move regardless of all other state.

## Motion State Model

The desired high-level transitions are:

```text
                         clear fault
                    +-------------------+
                    |                   v
startup --------> DISARMED <---------- FAULT
                    |
          +---------+----------+
          |                    |
     arm manual          start mission
          |                    |
          v                    v
       MANUAL             AUTONOMOUS
          |                    |
       disarm       cancel / finish / fail
          |                    |
          +---------+----------+
                    |
                    v
                 DISARMED

Any state -- emergency stop --> ESTOP
ESTOP -- explicit clear ------> DISARMED
```

Rules:

- startup remains `DISARMED`;
- changing mode invalidates retained intents using the existing mode
  generation;
- clearing `ESTOP` or `FAULT` returns to `DISARMED`, never directly to motion;
- manual takeover cancels the active mission before entering `MANUAL`;
- autonomous mode with no fresh autonomy intent commands a stop;
- command source, mode, limiting constraints, and stop reason are always
  visible to the operator.

## Typical User Flows

### Hardware commissioning

1. Open Settings.
2. Configure sensor drivers, buses, addresses, pins, ports, and frame IDs.
3. Enter measured wheelbase, rolling radius, encoder resolution, gear ratio,
   steering calibration, sensor transforms, and safety distances.
4. Confirm each publisher is running without communication errors.
5. With the vehicle stationary, verify:
   - encoder deltas remain zero;
   - IMU yaw rate is close to zero;
   - steering feedback is near physical center;
   - LiDAR geometry resembles the nearby environment;
   - timestamps remain fresh;
   - no safety stream is stale.
6. Close Settings and open the Autonomy workspace for motion tests.

Commissioning validates hardware. It does not build a useful map and never
starts autonomous driving.

### Manual mapping

This is the first production-worthy mapping workflow and does not require a
planner.

```text
Open Autonomy workspace
        |
Confirm sensor, odometry, and safety readiness
        |
Select "New local map"
        |
Clear grid and reset odometry origin
        |
Start mapping session
        |
Arm MANUAL mode
        |
Drive with keyboard or joystick while watching camera and map
        |
Stop and disarm
        |
Pause or finish mapping session
```

During the session:

- manual controls submit short-lived `MANUAL` intents;
- LiDAR safety may limit or stop forward speed;
- encoder distance and steering state update odometry;
- synchronized LiDAR scans are inserted at the estimated odometry pose;
- the UI draws the robot pose and odometry trail;
- stale odometry or LiDAR pauses scan insertion and explains why;
- emergency stop is always available.

For the initial fixed grid, the operator must remain inside the configured map
bounds. A rolling map or persistent global map is a later capability.

### Autonomous mapping

Autonomous mapping is a future explicit mission:

1. The user selects `Explore` and reviews speed and area limits.
2. The supervisor validates sensor freshness, odometry, safety, and mapping.
3. The user presses `Start exploration`.
4. The supervisor transitions the robot from `DISARMED` to `AUTONOMOUS`.
5. Exploration selects reachable local frontiers.
6. An Ackermann-aware planner and controller submit expiring autonomy intents.
7. The arbiter applies physical limits and current safety constraints.
8. The mapping session accumulates scans as the vehicle moves.
9. The user may pause, cancel, manually take over, or emergency-stop.
10. Completion, blockage, cancellation, or failure returns the robot to
    `DISARMED`.

Enabling local mapping is not equivalent to starting exploration.

### Navigate to a goal

Persistent-map navigation is a later workflow:

1. Load a saved map.
2. Establish or confirm the robot's initial map-relative pose.
3. Wait for localization state `tracking`.
4. Select a goal on the map.
5. Preview the Ackermann-feasible path and speed limits.
6. Press `Start navigation`.
7. Display live pose, path, goal, progress, command source, and safety state.
8. Finish, cancel, block, fail, or manually take over.

The goal picker must remain disabled when localization is unavailable or lost.

## Autonomy Workspace

### Route model

Add a dedicated route:

```text
/              camera-focused manual driving
/autonomy      mapping, pose, safety, modes, missions, and manual mapping
/virtual       compatibility alias or redirect to /autonomy?view=model
```

Do not use a boolean `virtual_mode` to conflate page navigation, view choice,
and simulation. Replace it eventually with independent concepts:

```text
operator view: camera | map | split | model
runtime source: hardware | mock-components | simulation
```

The existing `VirtualView` and `CarModelViewer` are useful scaffolding for the
model view. The model should be driven by `/odom`, steering state, scans, and
final commanded motion.

### Desktop layout

```text
+---------------------------------------------------------------------+
| MANUAL | Sensors healthy | Safety clear | E-STOP | Disarm           |
+-----------------------------------------------+---------------------+
|                                               | Mode                |
|                                               | o Disarmed          |
|            Map / Camera / Split / 3D          | * Manual            |
|                                               | o Autonomous        |
|       robot pose, trail, path, and goal        |                     |
|                                               | Mapping             |
|                                               | New Pause Clear     |
|                                               |                     |
|                                               | Mission             |
|                                               | No active mission   |
+-----------------------------------------------+---------------------+
| v 0.20 m/s | yaw 0.16 rad/s | obstacle 1.50 m | source: manual      |
+---------------------------------------------------------------------+
```

On mobile, the main visualization occupies the screen and operational state is
shown in a bottom sheet. Emergency stop must not be hidden inside the sheet.

### Always-visible operational information

- robot mode;
- armed/disarmed state;
- emergency stop and fault state;
- active mission and mission progress;
- final command source;
- commanded and measured speed;
- commanded and measured steering;
- pose and pose frame;
- nearest relevant obstacle;
- active safety limit and reason;
- sensor freshness and degraded state;
- mapping state and map frame.

The UI should explain stopped motion, for example:

```text
Stopped: robot is disarmed
Stopped: no fresh manual command
Stopped: waiting for a fresh LiDAR scan
Stopped: obstacle at 0.24 m
Stopped: encoder publisher unavailable
Stopped: navigation canceled by operator
```

### Settings integration

Settings retains configuration fields and a compact health summary. Replace
the large operational previews there with:

- a concise status row for LiDAR, IMU, encoders, steering, odometry, and map;
- calibration warnings;
- a small optional stationary scan preview;
- an `Open autonomy workspace` action.

Opening settings during motion should issue a stop. Changes that alter physical
calibration should reset dependent odometry or maps as already required by the
runtime hot-reload path.

## Mapping Session Contract

Mapping capability and mapping activity are different. Introduce an explicit
mapping session owned by a service or supervisor.

Suggested state:

```python
class MappingSessionState(str, Enum):
    IDLE = "idle"
    MAPPING = "mapping"
    PAUSED = "paused"
    COMPLETE = "complete"
    ERROR = "error"
```

Suggested session data:

```text
session_id
state
frame_id
started_monotonic_ns
updated_monotonic_ns
inserted_scans
rejected_scans
last_rejection_reason
map_sequence
robot_inside_bounds
error
```

Initial API surface:

```text
GET  /px/api/map/session
POST /px/api/map/session/start
POST /px/api/map/session/pause
POST /px/api/map/session/finish
POST /px/api/map/clear
POST /px/api/odometry/reset
GET  /px/api/map/current
```

Later persistent-map operations:

```text
POST /px/api/map/save
POST /px/api/map/load
GET  /px/api/maps
DELETE /px/api/maps/{name}
```

Rules:

- `start` validates LiDAR and odometry prerequisites;
- `start` does not change robot motion mode;
- `pause` stops grid modification without stopping sensor acquisition;
- `clear` requires confirmation and creates a new map sequence;
- odometry reset is explicit and reports the new origin;
- stale or unsynchronized inputs reject insertion without corrupting the grid;
- a persistent map must record resolution, dimensions, frame metadata, and the
  calibration identity used to create it.

The map should eventually be streamed rather than polled once per second.
Dense grids may use a compact binary or image representation while metadata and
small deltas remain typed.

## Mission Contract

Long-running autonomy behaviors use action-like semantics:

```text
prepare -> running -> succeeded
                   -> blocked
                   -> failed
                   -> canceling -> canceled
```

Every mission exposes:

- mission ID and type;
- creation and update timestamps;
- requested goal or limits;
- current state and progress;
- current path, if applicable;
- current stop/block reason;
- cancellation;
- final result;
- whether manual takeover is available.

Initial mission progression:

1. Drive a signed relative distance.
2. Drive a bounded steering arc.
3. Follow one local waypoint in `odom`.
4. Follow a local waypoint path.
5. Explore bounded local free space.
6. Navigate in a persistent map.

Relative motion is the first autonomous action because it exercises odometry,
timeouts, cancellation, arbitration, and safety without requiring global
planning.

## Coherent Simulation

Independent mocks remain useful for driver and UI tests, but a simulation mode
must derive all sensor outputs from one simulated plant:

```text
final actuator command
        |
        v
Ackermann kinematic vehicle in a simulated world
        |
        +--> ground-truth pose
        +--> encoder samples
        +--> steering-position samples
        +--> IMU samples
        +--> LiDAR ray casts against world geometry
```

Implementation status:

- `AckermannSimulationPlant` provides deterministic fixed-step, no-slip planar
  motion driven by the arbiter's final SI-unit actuator command;
- `CoherentSimulationService` publishes synchronized ground-truth, steering,
  rear-encoder, and IMU messages through the native TopicBus contracts;
- cumulative encoder rounding preserves sub-tick movement across updates;
- stale final commands stop the simulated vehicle through an independent
  simulation watchdog;
- the runtime can be enabled or disabled by hot settings reload without
  replacing the stable application service handles;
- a selectable drive boundary stops both sides during transitions, invalidates
  prior intents, returns the robot to `DISARMED`, and routes subsequent writes
  exclusively to physical hardware or an in-memory virtual sink;
- simulated encoder and IMU publishers replace their configured physical or
  per-device mock publishers, while passive topic monitors preserve sensor
  diagnostics and message counts;
- the operator workspace shows simulator lifecycle, physical isolation,
  ground-truth pose, speed, steering, encoder ticks, errors, freshness, and a
  safe reset action;
- world collision geometry and LiDAR ray casting remain follow-up work. LiDAR
  continues to use its independently configured hardware or mock source.

Required properties:

- deterministic clock or controllable time scale;
- configurable noise, bias, latency, and dropout;
- fixed obstacles and room geometry;
- collision handling;
- the same TopicBus message contracts as hardware;
- no frontend-only physics used as authoritative state;
- scenario reset and reproducible seeds;
- a visible distinction between ground truth and estimated odometry.

Simulation is selected as a hardware runtime setting, while operator view mode
remains independent. A user may view simulated data as a 2D map, camera-like
scene, split view, or 3D model. Enabling or resetting simulation never arms
motion; manual arming or an explicit autonomous action is still required.

## Safety Invariants

- No UI component, mission, mapper, planner, or sensor service writes directly
  to motors or steering hardware.
- Only the hardware controller applies the arbiter's final command.
- All manual and autonomy intents expire unless refreshed.
- Changing robot mode invalidates intents from the previous mode generation.
- Emergency stop is latched and wins over every intent.
- Fault clear and emergency-stop clear return to `DISARMED`.
- A stale required safety stream fails safe.
- Reverse behavior receives separate consideration; a front LiDAR must not be
  treated as complete reverse protection.
- Settings and destructive map operations cannot accidentally act as motion
  commands.
- Starting mapping never starts motion.
- Starting an autonomous mission requires an explicit final user action.

## Implementation Slices

### Slice 1: Operator workspace

- add `/autonomy`;
- reuse the existing map, scan, telemetry, controller, and 3D components;
- add camera, map, split, and model views;
- show robot mode, safety, pose, speed, and command reason;
- keep manual keyboard and joystick operation available on the route;
- leave compact diagnostics and a route link in Settings;
- preserve `/virtual` as a compatibility alias or redirect.

Acceptance:

- the user can manually drive while observing the map without opening Settings;
- telemetry connections are cleaned up when leaving the route;
- emergency stop remains visible and usable;
- the page works with mock sensors before LiDAR hardware is available;
- the 3D model consumes telemetry and does not create odometry.

### Slice 2: Explicit safety and mode operation

- start motion control in `DISARMED`;
- add Arm manual, Disarm, Emergency stop, Clear emergency stop, and Clear fault;
- expose final command source and current limiting reason;
- stop or disarm when entering high-risk settings or calibration flows;
- test stale commands, mode transitions, browser disconnect, and reconnect.

Acceptance:

- application startup cannot move the vehicle;
- manual commands work only after explicit arming;
- loss of manual heartbeat stops within the configured timeout;
- clearing a latched state never resumes old motion.

### Slice 3: Mapping sessions and odometry visualization

- add mapping session states and APIs;
- add clear, reset, start, pause, and finish operations;
- overlay robot pose and odometry trail on the map;
- expose insertion and rejection diagnostics;
- stream map updates or compact deltas;
- indicate map bounds and warn as the robot approaches them.

Acceptance:

- a stationary real encoder does not create apparent motion;
- manual driving expands the mapped area;
- stale odometry does not insert a scan;
- reset and clear operations are visible and deterministic;
- mapping may be paused without disabling sensor telemetry.

### Slice 4: Relative autonomous motion

- implement cancelable relative-distance and steering-arc actions;
- submit only expiring `AUTONOMY` intents;
- stop on completion, blockage, timeout, cancellation, stale odometry, or fault;
- show action feedback in the workspace.

Acceptance:

- distance and arc commands are plausible with mocks and measured hardware;
- LiDAR safety limits forward movement;
- cancellation stops promptly;
- manual takeover invalidates the autonomy command generation.

### Slice 5: Coherent simulator

- add an Ackermann plant and hot-reconfigurable lifecycle;
- derive encoders, steering, and IMU from plant state;
- isolate physical drive output and expose lifecycle/ground-truth status;
- add a simple world model and derive LiDAR from fixed world geometry;
- visualize estimated pose versus ground truth on the map;
- add deterministic scenarios for mapping and safety regression tests.

Acceptance:

- all simulated sensors agree on motion direction and timing;
- a stationary plant produces stationary encoders and odometry;
- enabling, disabling, and resetting simulation leave motion disarmed and
  physical drive isolated whenever the plant is active;
- obstacles remain fixed in world coordinates while the robot moves;
- map and safety tests are repeatable.

### Slice 6: Local waypoint navigation

- add one-goal and path-following actions in `odom`;
- enforce Ackermann turning radius;
- add path and goal overlays;
- add blocked-state and recovery hooks.

### Slice 7: Persistent localization and exploration

- choose native scan matching/SLAM or a ROS 2 bridge;
- save and load maps;
- localize against a map;
- implement bounded exploration and global navigation;
- keep the existing web app as the operator and orchestration layer.

## Test Strategy

Backend tests:

- state-transition tables for modes, mapping sessions, and missions;
- arbiter eligibility, expiration, generation invalidation, and constraints;
- mapping insertion at known poses and rejection of stale inputs;
- relative-motion completion and cancellation;
- endpoint idempotency and conflict behavior;
- simulator determinism and sensor agreement;
- shutdown and reconfiguration during active sessions.

Frontend tests:

- route entry and cleanup;
- view switching without restarting acquisition;
- mode and mission controls disabled by readiness state;
- persistent emergency-stop access;
- map-session actions and confirmations;
- correct rendering of command and stop reasons;
- settings popup inhibits motion while the operator workspace does not;
- responsive desktop and mobile layouts.

Hardware validation:

- encoder and steering signs for forward, reverse, left, and right;
- measured distance over several wheel rotations;
- odometry path during straight runs and fixed steering arcs;
- LiDAR transform against known walls;
- safety stop distance at increasing approach speeds;
- browser disconnect and backend restart while armed;
- emergency stop during manual and autonomous motion.

## First Milestone Definition of Done

The first operator-workflow milestone is complete when:

- `/autonomy` is the normal place to view scans, map, odometry, safety, and
  modes;
- Settings contains configuration and compact diagnostics rather than the main
  operational canvas;
- the user can close Settings, manually drive, and watch the local map update;
- the robot starts disarmed and requires explicit manual arming;
- emergency stop and current stop reason are always visible;
- mapping has explicit start, pause, clear, and reset semantics;
- the existing virtual model is a selectable telemetry visualization;
- no map or sensor toggle starts vehicle motion;
- the workflow works with component mocks and the coherent motion simulator,
  and is ready for a world-aware LiDAR simulator and navigation actions.

## Open Decisions

- Whether `/` remains the camera-first manual workspace or redirects into a
  unified operator workspace.
- Whether map updates use full compressed snapshots, tiles, or incremental
  cell updates.
- Whether the first fixed grid becomes rolling before persistent SLAM is added.
- Whether persistent localization is implemented natively or through ROS 2.
- How reverse safety is sensed on the physical RC chassis.
- Which map and mission data should be recorded for replay.
- Whether entering all settings disarms immediately or only opening robot
  hardware and calibration sections does so.

These decisions do not block the first route, explicit mapping session, or
manual mapping workflow.
