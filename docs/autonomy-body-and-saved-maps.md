# Body geometry, forward preference, and saved maps

Implemented September 2026. These additions do not start motion and do not
require changes to robot-hat.

## Overall length is not wheelbase

In **Hardware settings → Navigation geometry and policy**:

- `body_length_m`: frontmost to rearmost extent, including equipment. A 57 cm
  robot uses `0.57`; a 50 cm robot uses `0.50`.
- `body_width_m`: maximum centered lateral envelope, including wheels and
  protrusions. For an asymmetric chassis, use twice the larger distance from
  the longitudinal centerline to either side.
- `rear_overhang_m`: rear axle center to the rearmost extent.
- `use_body_clearance`: opt into measured-envelope checks once all three
  measurements are known. Incomplete or invalid measurements are rejected.

Keep `ackermann_odometry.wheelbase_m` equal to the measured front-to-rear axle
distance. Do not put the overall length there: it changes steering curvature
and odometry. Front overhang is overall length minus rear overhang minus
wheelbase; verify that these physical measurements are consistent.

Dimensions default to unset; body clearance defaults off to preserve existing
configurations. Entering a length alone records it but does not enable the
envelope. These additive fields remain compatible with schema version 7; no
configuration migration or automatic calibration rewrite is required.

### Current collision model and limitations

The odometry reference is the rear axle. The enclosing circle radius is:

```
radius = hypot(max(rear_overhang, length - rear_overhang), width / 2)
```

Planning inflates occupied/unknown cells by this radius **plus the requested
route clearance**. It also adds a grid-resolution allowance for the spatial
extent of occupied and traversed cells. Thus the default 0.20 m route clearance
is additional margin, not the body radius. Map edges remain protected.

Simulation uses the larger of this radius and
`coherent_simulation.vehicle_radius_m` for collision checks and initial-pose
validation. A previously valid simulated starting position may therefore be
rejected after enabling a larger body envelope.

This is a conservative circle, **not an orientation-aware rectangular or swept
body footprint**. It may reject tight corridors/corners where the real chassis
could fit. A future heading-aware footprint should improve accessibility
without reducing the specified body dimensions. Live LiDAR sector stop/slow
distances remain separately configured; this setting is not a substitute for
physical safety calibration, sensor coverage, or supervised low-speed tests.

Navigation policy and envelope changes currently require a backend restart;
the settings store reports this. They are not part of the simulator's existing
hot-reload group.

## Forward-preferred navigation

`navigation.prefer_forward` defaults to true in the application runtime.
The planner first tries its existing forward grid-route smoothing. If that
fails curvature/collision validation, it tries a forward-only Hybrid A* search
before allowing reverse recovery. `forward_search_nodes` bounds that additional
search (default 3,000 expansions).

Reverse remains available when the forward search cannot find a route within
its budget. This is a preference, not a guarantee of forward travel or globally
optimal travel time. It does not optimize waypoint arrival heading against
future mission legs. Setting the preference false restores the previous
reverse-capable recovery behavior.

## Saving and loading a map

1. Start mapping and manually scan as usual. Pause or Finish when ready.
2. Expand **Mapping session → Saved maps**, enter a name, and choose **Save
   current map**. Finish alone retains the map only in memory.
3. The backend writes a new, versioned JSON snapshot atomically under
   `autonomy-maps/` beside its active `config.json`. On this Mac's normal
   configuration this is
   `/Users/km/Library/Application Support/picar-x-racer/autonomy-maps/`.
4. After restarting, enable the normal localization inputs, remain disarmed,
   and pause/finish mapping if active. Refresh/select the saved map.
5. Supply the robot's **current rear-axle X, Y and heading in the saved map's
   coordinates**. The saved pose is shown only as a reference, not autofilled:
   the robot may have moved since saving. Heading follows the map convention,
   0° along +X and positive counterclockwise; it is not the servo steering angle.
6. Confirm placement and choose **Load at this placement**. The backend checks
   disarmed state, no active navigation, a fresh fused pose, and known free
   space at the supplied saved-map position. It rechecks state after disk I/O.
7. The saved grid is rigidly aligned into the current odometry frame. Loading
   does not teleport the estimator, move the vehicle, or start a mission. Check
   scan/map alignment, then select and review a fresh route before driving.

Loaded maps are frozen localization references; Resume/Start is disabled until
Clear/Reset removes that reference. New scan insertion into a rotated loaded
map, automatic global relocalization, automatic latest-map restoration,
calibration-identity compatibility checking, and map deletion are not implemented.
Manual placement must be close enough for the configured scan matcher to track;
the free-cell check cannot prove that the physical robot is really there or
that its entire body fits. Verify calibration, frame conventions, and environment
before reusing a map. Use the observed-map scan-matching mode if corrections
should come from the saved scan rather than simulator ground-truth geometry.

The dashed simulator floor-plan overlay is separate from observed occupancy
and is not changed by Save/Load. Only the learned occupancy grid is persisted;
routes, loop execution state, and motion authorization are not restored.

API:

```
GET  /px/api/maps                     list snapshots, newest first
POST /px/api/maps                     {"name": "Flat"}
POST /px/api/maps/{id}/load           {"x_m": 1.2, "y_m": -0.3, "yaw_deg": 90}
```

Snapshots retain dimensions, resolution, origin/rotation, occupancy cells and
optional save-time pose. IDs are server-generated and validated; loads are
size-bounded. Saves create new files and never overwrite an existing map.
Unsaved live occupancy is replaced by an explicitly confirmed load; saved
files remain available across Clear/Reset and backend restarts.
