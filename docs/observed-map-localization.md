# Localization against an observed map

This milestone adds local LiDAR pose corrections against a paused or finished
occupancy map. It works with real sensor publishers and coherent simulation.
Unlike the simulation-reference matcher, it never reads simulator obstacle
geometry or ground-truth pose. No new robot-hat driver is needed.

## Operator workflow

1. Enable and configure encoder odometry, pose estimation, LiDAR, and local
   mapping. An IMU is recommended. For laptop development, enable coherent
   simulation so commands, encoders, IMU, and LiDAR describe the same motion.
2. Under **Pose estimation**, disable **Simulation known-world scan matching**
   and enable **Observed-map localization**. Save both changes together; the
   sources are mutually exclusive. The default search settings are a starting
   point, not a substitute for hardware calibration.
3. In the autonomy workspace, start mapping and drive manually at low speed.
   The map is built from measured scans and wheel/IMU-fused poses. Observed-map
   corrections wait while mapping is active, avoiding matching a scan against
   a map that is being updated from that same scan.
4. Pause or finish mapping. The retained map becomes the localization reference.
   With fresh poses and scans, diagnostics should change from **Waiting for
   frozen map** to **Correcting**, and the corrected-scan count should increase.
   A map needs enough observed obstacle cells and locally distinctive geometry.
5. Drive manually to inspect the correction, or review and start a goal/mission
   using the existing controls. Enabling localization never starts robot motion.
6. Starting mapping again suspends observed-map corrections. Pause or finish
   again to use the updated reference. Clear/reset invalidates the reference
   until another nonempty map is built.

Switching correction sources or tuning their search settings hot-reloads only
the matcher. It does not reset fused localization or clear the map. Changes to
odometry, mapping geometry, or other frame-defining settings still follow the
existing reset/reconfiguration rules.

For a development comparison, you can build a map with the known-world matcher
enabled and switch to observed-map matching after freezing it. This is useful
for isolating localization errors from mapping drift, but it is **not** an
independent test of real-world map building: its reference benefited from
simulator geometry during construction.

## Configuration

The new block is `pose_estimation.occupancy_map_scan_matching`. It is disabled
by default and additive: existing schema-version-7 configurations remain valid,
so this feature does not introduce a version-8 migration.

Common settings control local translation/heading search, scan-point sampling,
maximum mean residual, source-pose freshness, and correction uncertainty.
Additional settings control occupied-cell threshold, minimum occupied cells,
minimum observed endpoint overlap, and ambiguity probes. The default local
search spans ±0.15 m in X/Y and ±8° in heading. Alignment at its boundary is
rejected; this is not a facility for recovering from an arbitrary starting pose.

Distances are measured to occupied cell centers using a cached, bounded
eight-neighbor distance field with interpolation. Unknown/out-of-map endpoints
receive the residual cap. Candidate poses must originate in observed free space.
Nearby alternative translations/headings are probed and similarly scoring
alignments rejected. This is a heuristic ambiguity check, not a proof of global
uniqueness. Position uncertainty is never smaller than the map cell size.
Search work is bounded to 500,000 sampled-point evaluations and reference maps
to one million cells; expensive reference construction and matching run off the
event loop with a latest-scan queue.

## Runtime integration and diagnostics

- `/mapping/session` publishes mapping state alongside `/map`. A frozen reference
  requires an enabled session with a map, an inactive insertion state, and a
  matching map sequence.
- A scan must be newer than the reference snapshot and have a sufficiently fresh
  causal fused-pose prior in the same frame.
- Map/session identity is checked after asynchronous work. Restarting mapping,
  replacing the map, or resetting it discards an in-flight correction.
- Accepted corrections use the existing `/localization/observation` topic with
  source `occupancy_map_scan_matcher`; the existing estimator handles fusion.
- Scan-matching diagnostics identify `occupancy_map` versus `known_world`, expose
  the reference-map sequence and rejected-reference count, and retain rejection
  reasons such as insufficient overlap, ambiguity, or the local search boundary.
- Session recordings now include mapping-state transitions. Replay can inspect
  these events and use recorded corrections; it does not rerun this matcher.

## Limits and follow-up work

This is frozen-map localization, not full SLAM. It does not repair drift already
present in the map, perform loop closure, maintain a separate global map frame,
persist maps across backend restarts, or globally relocalize a lost robot.
Scanning slowly and calibrating drivetrain distance, steering geometry, IMU
orientation, and LiDAR extrinsics remain important. Moving obstacles and sparse
or repetitive geometry can cause corrections to be rejected. Live LiDAR safety
remains separate from this frozen localization reference.

The current planar scan model also has no per-ray motion deskew. Validate timing,
performance, and geometry with the actual RPLIDAR C1 before relying on this on
hardware. Useful next steps are recorded-drive evaluations with sensor faults,
calibration exercises, and then map correction/loop closure.
