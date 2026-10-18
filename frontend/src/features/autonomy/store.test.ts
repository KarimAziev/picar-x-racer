import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { ref } from "vue";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  initWS: vi.fn(),
  cleanup: vi.fn(),
  options: null as null | { onMessage?: (message: unknown) => void },
}));

vi.mock("@/api", () => ({
  robotApi: { get: mocks.get, post: mocks.post },
}));

vi.mock("@/composables/useWebsocket", () => ({
  useWebSocket: (options: { onMessage?: (message: unknown) => void }) => {
    mocks.options = options;
    return {
      initWS: mocks.initWS,
      cleanup: mocks.cleanup,
      closeWS: vi.fn(),
      retry: vi.fn(),
      send: vi.fn(),
      connected: ref(true),
      active: ref(true),
      loading: ref(false),
      reconnectEnabled: ref(true),
      ws: ref(null),
    };
  },
}));

import { useAutonomyStore } from "@/features/autonomy/store";

describe("autonomy telemetry store", () => {
  it("saves a named map without starting motion or changing the current map", async () => {
    const store = useAutonomyStore();
    const saved = { id: "a".repeat(32), name: "Flat", created_at: "2026-09-10T10:00:00Z", saved_pose: null };
    mocks.post.mockResolvedValueOnce(saved);
    expect(await store.saveMap("Flat")).toBe(true);
    expect(mocks.post).toHaveBeenCalledExactlyOnceWith("/px/api/maps", { name: "Flat" });
    expect(store.savedMaps).toEqual([saved]);
    expect(store.savedMapMessage).toContain("survive a backend restart");
    expect(store.savedMapBusy).toBe(false);
  });

  it("keeps saved-map errors visible across successful catalog refreshes", async () => {
    const store = useAutonomyStore();
    mocks.post.mockRejectedValueOnce(new Error("Disarm first"));
    expect(await store.loadSavedMap("a".repeat(32), { x_m: 0, y_m: 0, yaw_deg: 0 })).toBe(false);
    const error = store.savedMapError;
    expect(error).toBeTruthy();
    mocks.get.mockResolvedValueOnce([]);
    await store.refreshSavedMaps();
    expect(store.savedMapError).toBe(error);
    expect(store.mapClearGeneration).toBe(0);
    expect(mocks.post).toHaveBeenCalledTimes(1);
  });

  it("loads explicit placement and discards old route previews without motion", async () => {
    const store = useAutonomyStore();
    mocks.post.mockResolvedValue({ enabled: true, state: "paused", loaded_from_disk: true, has_map: true });
    const alignment = { x_m: 1.2, y_m: -0.3, yaw_deg: 90 };
    expect(await store.loadSavedMap("b".repeat(32), alignment)).toBe(true);
    expect(mocks.post).toHaveBeenCalledWith(`/px/api/maps/${"b".repeat(32)}/load`, alignment);
    expect(store.mapClearGeneration).toBe(1);
    expect(store.mappingSession?.loaded_from_disk).toBe(true);
    expect(mocks.post.mock.calls.some(([path]) => String(path).endsWith("/start"))).toBe(false);
  });

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.options = null;
    mocks.get.mockImplementation((path: string) => {
      if (path === "/px/api/map/session") {
        return Promise.resolve({
          enabled: true,
          state: "idle",
          session_id: 0,
          map_sequence: 0,
          scans_received: 0,
          scans_inserted: 0,
          returns_inserted: 0,
          ignored_inactive_scans: 0,
          rejected_missing_odometry: 0,
          rejected_stale_odometry: 0,
          preferred_pose_source: "localization",
          active_pose_source: null,
          scans_inserted_with_odometry: 0,
          scans_inserted_with_localization: 0,
          localization_fallbacks: 0,
          has_map: false,
        });
      }
      if (path === "/px/api/map/current") {
        return Promise.resolve({
          header: {
            sequence: 1,
            frame_id: "odom",
            timestamp_monotonic_ns: 1,
            source_timestamp_ns: null,
          },
          width: 1,
          height: 1,
          resolution_m: 0.1,
          origin_x_m: 0,
          origin_y_m: 0,
          origin_yaw_rad: 0,
          data: [-1],
        });
      }
      if (path === "/px/api/autonomy/relative-motion") {
        return Promise.resolve({ available: true, state: "idle" });
      }
      if (path === "/px/api/autonomy/navigation/plan") {
        return Promise.resolve({
          available: true,
          state: "idle",
          frame_id: "odom",
          goal: null,
          start: null,
          path: [],
          path_directions: [],
          path_length_m: 0,
          reverse_distance_m: 0,
          gear_changes: 0,
          clearance_m: 0.2,
          allow_unknown: false,
          map_sequence: null,
          pose_source: null,
          start_yaw_rad: null,
          expanded_nodes: 0,
          planning_method: "grid_astar",
          geometry_validated: false,
          smoothed: false,
          raw_waypoint_count: 0,
          max_curvature_per_m: null,
          curvature_limit_per_m: null,
          minimum_turning_radius_m: null,
          initial_heading_error_deg: null,
          reason: "Click a free map location to preview a route",
        });
      }
      if (path === "/px/api/autonomy/navigation/execution") {
        return Promise.resolve({
          available: true,
          state: "idle",
          action_id: null,
          goal: null,
          current_pose: null,
          map_sequence: null,
          path_length_m: 0,
          progress_m: 0,
          remaining_m: 0,
          target_waypoint_index: null,
          max_speed_mps: null,
          commanded_speed_mps: 0,
          motion_direction: null,
          gear_changes_completed: 0,
          gear_changes_total: 0,
          steering_angle_deg: 0,
          cross_track_error_m: 0,
          reason: "Select and review a navigation goal",
        });
      }
      if (path === "/px/api/autonomy/navigation/mission/plan") {
        return Promise.resolve({
          available: true,
          state: "idle",
          frame_id: "odom",
          mode: "once",
          lap_count: 1,
          targets: [],
          legs: [],
          map_sequence: null,
          total_path_length_m: 0,
          total_reverse_distance_m: 0,
          reason: "Add map targets, then review the complete mission",
        });
      }
      if (path === "/px/api/autonomy/navigation/mission/execution") {
        return Promise.resolve({
          available: true,
          state: "idle",
          mission_id: null,
          mode: "once",
          current_lap: 0,
          total_laps: 1,
          active_target_index: null,
          completed_target_visits: 0,
          total_target_visits: 0,
          map_sequence: null,
          current_leg_path_length_m: 0,
          completed_distance_m: 0,
          reason: "Review a mission before starting it",
        });
      }
      if (path === "/px/api/autonomy/simulation") {
        return Promise.resolve({
          enabled: true,
          running: true,
          physical_drive_isolated: true,
          published_updates: 42,
          latest_state: {
            header: {
              sequence: 42,
              frame_id: "world",
              timestamp_monotonic_ns: 420,
              source_timestamp_ns: 410,
            },
            x_m: 1.2,
            y_m: -0.5,
            yaw_rad: 0.25,
            linear_speed_mps: 0.2,
            steering_angle_rad: 0.1,
            yaw_rate_radps: 0.08,
            longitudinal_acceleration_mps2: 0,
            lateral_acceleration_mps2: 0.016,
            encoder_ticks: 1200,
          },
          error: null,
        });
      }
      if (path === "/px/api/autonomy/localization") {
        return Promise.resolve({
          enabled: true,
          running: true,
          published_updates: 40,
          imu_updates_used: 38,
          imu_updates_rejected: 1,
          corrections_applied: 0,
          corrections_rejected: 0,
          last_position_innovation_m: null,
          last_heading_innovation_rad: null,
          latest_pose: null,
          error: null,
        });
      }
      if (path === "/px/api/autonomy/localization/scan-matching") {
        return Promise.resolve({
          enabled: true,
          running: true,
          scans_received: 12,
          matches_published: 10,
          rejected_missing_pose: 1,
          rejected_pose_timing: 0,
          rejected_insufficient_points: 0,
          rejected_quality: 1,
          last_mean_error_m: 0.018,
          last_prior_mean_error_m: 0.064,
          last_valid_points: 48,
          last_candidates_evaluated: 686,
          latest_observation: null,
          last_rejection: null,
          error: null,
        });
      }
      return Promise.resolve({
        sensors: [
          {
            sensor: "imu",
            enabled: true,
            running: true,
            published_messages: 12,
            last_timestamp_monotonic_ns: 100,
            error: null,
          },
        ],
      });
    });
  });

  it("fetches publisher status", async () => {
    const store = useAutonomyStore();

    await store.refreshStatus();

    expect(mocks.get).toHaveBeenCalledWith("/px/api/sensors/status");
    expect(store.sensors[0].published_messages).toBe(12);
  });

  it("keeps the newest telemetry envelope by channel", () => {
    const store = useAutonomyStore();
    store.initialize();

    mocks.options?.onMessage?.({
      channel: "encoder",
      topic: "/encoder/state",
      payload: {
        header: {
          sequence: 2,
          frame_id: "encoder",
          timestamp_monotonic_ns: 200,
          source_timestamp_ns: 190,
        },
        left: { ticks: 42, delta_ticks: 3 },
        right: { ticks: 44, delta_ticks: 5 },
      },
    });

    expect(mocks.initWS).toHaveBeenCalledOnce();
    expect(store.latest.encoder?.payload).toMatchObject({
      left: { ticks: 42, delta_ticks: 3 },
      right: { ticks: 44, delta_ticks: 5 },
    });

    store.cleanup();
    expect(mocks.cleanup).toHaveBeenCalledOnce();
  });

  it("receives steering position independently of drive encoders", () => {
    const store = useAutonomyStore();
    store.initialize();
    mocks.options?.onMessage?.({
      channel: "steering",
      topic: "/steering/position",
      payload: {
        header: {
          sequence: 1,
          frame_id: "base_link",
          timestamp_monotonic_ns: 200,
          source_timestamp_ns: null,
        },
        sensor_angle_deg: 190,
        wheel_angle_rad: Math.PI / 18,
      },
    });
    expect(store.latest.steering?.payload).toMatchObject({
      sensor_angle_deg: 190,
      wheel_angle_rad: Math.PI / 18,
    });
    expect(store.latest.encoder).toBeUndefined();
    store.cleanup();
  });

  it("keeps fused pose telemetry and localization runtime status", async () => {
    const store = useAutonomyStore();
    store.initialize();

    mocks.options?.onMessage?.({
      channel: "localization",
      topic: "/pose",
      payload: {
        header: {
          sequence: 3,
          frame_id: "odom",
          timestamp_monotonic_ns: 300,
          source_timestamp_ns: null,
        },
        child_frame_id: "base_link",
        x_m: 0.4,
        y_m: -0.1,
        yaw_rad: 0.2,
        linear_speed_mps: 0.15,
        yaw_rate_radps: 0.05,
        position_variance_m2: 0.001,
        yaw_variance_rad2: 0.002,
        fusion_mode: "wheel_imu",
        last_correction_source: null,
      },
    });
    await store.refreshLocalization();

    expect(mocks.get).toHaveBeenCalledWith("/px/api/autonomy/localization");
    const localization = store.latest.localization;
    expect(localization?.channel).toBe("localization");
    expect(
      localization?.channel === "localization"
        ? localization.payload.x_m
        : null,
    ).toBe(0.4);
    expect(store.localization?.imu_updates_used).toBe(38);
  });

  it("keeps scan-matching quality diagnostics", async () => {
    const store = useAutonomyStore();

    await store.refreshScanMatching();

    expect(mocks.get).toHaveBeenCalledWith(
      "/px/api/autonomy/localization/scan-matching",
    );
    expect(store.scanMatching?.matches_published).toBe(10);
    expect(store.scanMatching?.last_mean_error_m).toBe(0.018);
  });

  it("retrieves and operates the explicit mapping session", async () => {
    const store = useAutonomyStore();
    mocks.post.mockResolvedValue({
      enabled: true,
      state: "active",
      session_id: 1,
      map_sequence: 0,
      scans_received: 0,
      scans_inserted: 0,
      returns_inserted: 0,
      ignored_inactive_scans: 0,
      rejected_missing_odometry: 0,
      rejected_stale_odometry: 0,
      preferred_pose_source: "localization",
      active_pose_source: "localization",
      scans_inserted_with_odometry: 0,
      scans_inserted_with_localization: 1,
      localization_fallbacks: 0,
      has_map: false,
    });

    await store.refreshMappingSession();
    await store.runMappingAction("start");
    await store.runMappingAction("clear");

    expect(mocks.get).toHaveBeenCalledWith("/px/api/map/session");
    expect(mocks.post).toHaveBeenCalledWith("/px/api/map/session/start");
    expect(mocks.post).toHaveBeenCalledWith("/px/api/map/session/clear");
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/plan/clear",
    );
    expect(store.mappingSession?.state).toBe("active");
    expect(store.mappingSession?.session_id).toBe(1);
    expect(store.mapClearGeneration).toBe(1);
  });

  it("does not start mapping while navigation is active", async () => {
    const store = useAutonomyStore();
    await store.refreshNavigationExecution();
    store.navigationExecution = {
      ...store.navigationExecution!,
      state: "running",
      action_id: "navigation-1",
    };
    vi.clearAllMocks();

    await store.runMappingAction("start");

    expect(mocks.post).not.toHaveBeenCalled();
    expect(store.mappingActionError).toContain("Cancel the active navigation");
  });

  it("clears a stale route preview when the map disappears", async () => {
    const store = useAutonomyStore();
    store.navigationPlan = {
      available: true,
      state: "ready",
      frame_id: "odom",
      goal: { x_m: 1, y_m: 1 },
      start: { x_m: 0, y_m: 0 },
      path: [
        { x_m: 0, y_m: 0 },
        { x_m: 1, y_m: 1 },
      ],
      path_directions: ["forward"],
      path_length_m: 1.41,
      reverse_distance_m: 0,
      gear_changes: 0,
      clearance_m: 0.2,
      allow_unknown: false,
      map_sequence: 2,
      pose_source: "localization",
      start_yaw_rad: 0,
      expanded_nodes: 4,
      planning_method: "hybrid_astar",
      geometry_validated: true,
      smoothed: true,
      raw_waypoint_count: 2,
      max_curvature_per_m: 1.2,
      curvature_limit_per_m: 3.2,
      minimum_turning_radius_m: 0.31,
      initial_heading_error_deg: 12,
      reason: null,
    };
    mocks.get.mockRejectedValueOnce({ response: { status: 404 } });
    mocks.post.mockResolvedValue({
      available: true,
      state: "idle",
      frame_id: "odom",
      goal: null,
      start: null,
      path: [],
      path_directions: [],
      path_length_m: 0,
      reverse_distance_m: 0,
      gear_changes: 0,
      clearance_m: 0.2,
      allow_unknown: false,
      map_sequence: null,
      pose_source: null,
      start_yaw_rad: null,
      expanded_nodes: 0,
      planning_method: "grid_astar",
      geometry_validated: false,
      smoothed: false,
      raw_waypoint_count: 0,
      max_curvature_per_m: null,
      curvature_limit_per_m: null,
      minimum_turning_radius_m: null,
      initial_heading_error_deg: null,
      reason: "Click a free map location to preview a route",
    });

    await store.refreshLocalMap();

    expect(store.localMap).toBeNull();
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/plan/clear",
    );
    expect(store.navigationPlan?.state).toBe("idle");
  });

  it("reports the reactive websocket connection state", () => {
    const store = useAutonomyStore();

    store.initialize();

    expect(store.connected).toBe(true);
  });

  it("starts a relative-distance action with SI values", async () => {
    const store = useAutonomyStore();
    mocks.post.mockResolvedValue({
      available: true,
      state: "running",
      action_id: "action-1",
      distance_m: 0.5,
      requested_speed_mps: 0.15,
      progress_m: 0,
      remaining_m: 0.5,
      reason: null,
    });

    await store.refreshRelativeMotion();
    await store.startRelativeDistance(0.5, 0.15);

    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/relative-motion/distance",
      { distance_m: 0.5, speed_mps: 0.15 },
    );
    expect(store.relativeMotion?.state).toBe("running");
  });

  it("plans and clears an arbitrary map goal without starting motion", async () => {
    const store = useAutonomyStore();
    mocks.post.mockImplementation((path: string) => {
      if (path === "/px/api/autonomy/navigation/plan") {
        return Promise.resolve({
          available: true,
          state: "ready",
          frame_id: "odom",
          goal: { x_m: 1.2, y_m: -0.4 },
          start: { x_m: 0, y_m: 0 },
          path: [
            { x_m: 0, y_m: 0 },
            { x_m: 1.2, y_m: -0.4 },
          ],
          path_directions: ["forward"],
          path_length_m: 1.26,
          reverse_distance_m: 0,
          gear_changes: 0,
          clearance_m: 0.2,
          allow_unknown: false,
          map_sequence: 12,
          pose_source: "localization",
          start_yaw_rad: 0.1,
          expanded_nodes: 17,
          planning_method: "grid_astar",
          geometry_validated: true,
          smoothed: true,
          raw_waypoint_count: 2,
          max_curvature_per_m: 1.1,
          curvature_limit_per_m: 3.2,
          minimum_turning_radius_m: 0.31,
          initial_heading_error_deg: -8,
          reason: "Route preview is ready; no motion command has been issued",
        });
      }
      return Promise.resolve({
        available: true,
        state: "idle",
        frame_id: "odom",
        goal: null,
        start: null,
        path: [],
        path_directions: [],
        path_length_m: 0,
        reverse_distance_m: 0,
        gear_changes: 0,
        clearance_m: 0.2,
        allow_unknown: false,
        map_sequence: null,
        pose_source: null,
        start_yaw_rad: null,
        expanded_nodes: 0,
        planning_method: "grid_astar",
        geometry_validated: false,
        smoothed: false,
        raw_waypoint_count: 0,
        max_curvature_per_m: null,
        curvature_limit_per_m: null,
        minimum_turning_radius_m: null,
        initial_heading_error_deg: null,
        reason: "Click a free map location to preview a route",
      });
    });

    await store.refreshNavigationPlan();
    await store.planNavigationGoal(1.2, -0.4);

    expect(mocks.get).toHaveBeenCalledWith("/px/api/autonomy/navigation/plan");
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/plan",
      {
        x_m: 1.2,
        y_m: -0.4,
        clearance_m: 0.2,
        allow_unknown: false,
      },
    );
    expect(store.navigationPlan?.state).toBe("ready");
    expect(store.navigationPlan?.path).toHaveLength(2);

    await store.clearNavigationPlan();
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/plan/clear",
    );
    expect(store.navigationPlan?.state).toBe("idle");
  });

  it("starts and controls navigation execution explicitly", async () => {
    const store = useAutonomyStore();
    const execution = {
      available: true,
      state: "running",
      action_id: "navigation-1",
      goal: { x_m: 1, y_m: 0 },
      current_pose: { x_m: 0, y_m: 0 },
      map_sequence: 4,
      path_length_m: 1,
      progress_m: 0,
      remaining_m: 1,
      target_waypoint_index: 1,
      max_speed_mps: 0.15,
      commanded_speed_mps: 0.15,
      motion_direction: "forward",
      gear_changes_completed: 0,
      gear_changes_total: 0,
      steering_angle_deg: 0,
      cross_track_error_m: 0,
      reason: "Following the reviewed route",
    };
    mocks.post.mockResolvedValue(execution);

    await store.startNavigation(0.15);
    await store.runNavigationAction("pause");
    await store.runNavigationAction("resume");
    await store.runNavigationAction("cancel");

    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/execution/start",
      {
        max_speed_mps: 0.15,
        lookahead_m: 0.25,
        goal_tolerance_m: 0.08,
      },
    );
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/execution/pause",
    );
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/execution/resume",
    );
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/execution/cancel",
    );
    expect(store.navigationExecution?.action_id).toBe("navigation-1");
  });

  it("builds, reviews, and starts an ordered loop mission", async () => {
    const store = useAutonomyStore();
    const idlePlan = {
      available: true,
      state: "idle",
      frame_id: "odom",
      mode: "loop",
      lap_count: 2,
      targets: [],
      legs: [],
      map_sequence: null,
      total_path_length_m: 0,
      total_reverse_distance_m: 0,
      reason: "Add map targets",
    };
    mocks.post.mockImplementation((path: string) => {
      if (path.endsWith("/plan/clear")) return Promise.resolve(idlePlan);
      if (path.endsWith("/mission/plan")) {
        return Promise.resolve({
          ...idlePlan,
          state: "ready",
          targets: store.missionTargets,
          map_sequence: 8,
          total_path_length_m: 4.2,
          reason: "Validated 3 route legs",
        });
      }
      return Promise.resolve({
        available: true,
        state: "running",
        mission_id: "mission-1",
        mode: "loop",
        current_lap: 0,
        total_laps: 2,
        active_target_index: 0,
        completed_target_visits: 0,
        total_target_visits: 5,
        map_sequence: 8,
        current_leg_path_length_m: 1,
        completed_distance_m: 0,
        reason: "Following live route",
      });
    });

    store.navigationMissionMode = "loop";
    store.navigationMissionLapCount = 2;
    await store.addMissionTarget(1, 0);
    await store.addMissionTarget(2, 1);
    await store.reviewNavigationMission();
    await store.startNavigationMission(0.2);

    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/mission/plan",
      {
        targets: [
          { x_m: 1, y_m: 0, dwell_seconds: 0 },
          { x_m: 2, y_m: 1, dwell_seconds: 0 },
        ],
        mode: "loop",
        lap_count: 2,
        clearance_m: 0.2,
        allow_unknown: false,
      },
    );
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/mission/execution/start",
      {
        max_speed_mps: 0.2,
        lookahead_m: 0.25,
        goal_tolerance_m: 0.08,
      },
    );
    expect(store.navigationMissionExecution?.mission_id).toBe("mission-1");
  });

  it("blocks planning and execution while the map is changing", async () => {
    const store = useAutonomyStore();
    await store.refreshMappingSession();
    store.mappingSession = { ...store.mappingSession!, state: "active" };

    await store.planNavigationGoal(1, 1);
    await store.startNavigation();

    expect(mocks.post).not.toHaveBeenCalled();
    expect(store.navigationPlanError).toContain("Pause or finish mapping");
    expect(store.navigationExecutionError).toContain("Pause or finish mapping");
  });

  it("keeps a navigation command error across background status polls", async () => {
    const store = useAutonomyStore();
    store.navigationExecutionError = "The occupancy map changed.";

    await store.refreshNavigationExecution();

    expect(store.navigationExecution?.state).toBe("idle");
    expect(store.navigationExecutionError).toBe("The occupancy map changed.");
  });

  it("clears a recovered navigation status-poll error", async () => {
    const store = useAutonomyStore();
    store.navigationExecutionStatusError = "Control server unavailable.";

    await store.refreshNavigationExecution();

    expect(store.navigationExecution?.state).toBe("idle");
    expect(store.navigationExecutionStatusError).toBeNull();
  });

  it("starts a relative steering arc with SI distance and speed", async () => {
    const store = useAutonomyStore();
    mocks.post.mockResolvedValue({
      available: true,
      state: "running",
      action_id: "arc-1",
      action_type: "arc",
      distance_m: 0.3,
      requested_speed_mps: 0.12,
      progress_m: 0,
      remaining_m: 0.3,
      steering_angle_deg: -15,
      target_yaw_rad: 0.32,
      yaw_progress_rad: 0,
      reason: null,
    });

    await store.startRelativeArc(0.3, 0.12, -15);

    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/relative-motion/arc",
      {
        distance_m: 0.3,
        speed_mps: 0.12,
        steering_angle_deg: -15,
      },
    );
    expect(store.relativeMotion?.action_type).toBe("arc");
  });

  it("keeps simulation status and safely resets through the runtime endpoint", async () => {
    const store = useAutonomyStore();
    mocks.post.mockResolvedValue({
      enabled: true,
      running: true,
      physical_drive_isolated: true,
      published_updates: 0,
      latest_state: {
        x_m: 0,
        y_m: 0,
        yaw_rad: 0,
        linear_speed_mps: 0,
        steering_angle_rad: 0,
        yaw_rate_radps: 0,
        longitudinal_acceleration_mps2: 0,
        lateral_acceleration_mps2: 0,
        encoder_ticks: 0,
      },
      error: null,
    });

    await store.refreshSimulation();
    await store.resetSimulation();

    expect(mocks.get).toHaveBeenCalledWith("/px/api/autonomy/simulation");
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/simulation/reset",
    );
    expect(mocks.post).toHaveBeenCalledWith(
      "/px/api/autonomy/navigation/plan/clear",
    );
    expect(mocks.get).toHaveBeenCalledWith("/px/api/map/session");
    expect(mocks.get).toHaveBeenCalledWith("/px/api/map/current");
    expect(store.mapClearGeneration).toBe(1);
    expect(store.simulation?.published_updates).toBe(0);
    expect(store.simulation?.physical_drive_isolated).toBe(true);
    expect(store.simulationLastUpdatedAt).not.toBeNull();
  });

  it("refreshes the live route and mission together, including terminal route clearing", async () => {
    const store = useAutonomyStore();
    await store.refreshNavigationPlan();
    const idleRoute = store.navigationPlan;
    const liveRoute = { ...idleRoute, state: "ready", path: [
      { x_m: 0.3, y_m: 0.1 }, { x_m: 1, y_m: 1 },
    ] };
    store.navigationMissionExecutionError = "Start was rejected";
    mocks.get.mockResolvedValueOnce({
      mission: { state: "running", active_target_index: 1 },
      execution: { state: "running", action_id: "new-leg" },
      route: liveRoute,
    });
    await store.refreshNavigationMissionRuntime();
    expect(store.navigationPlan?.path[0]).toEqual({ x_m: 0.3, y_m: 0.1 });
    expect(store.navigationExecution?.action_id).toBe("new-leg");
    expect(store.navigationMissionExecution?.active_target_index).toBe(1);
    expect(store.navigationMissionExecutionError).toBe("Start was rejected");
    mocks.get.mockResolvedValueOnce({
      mission: { state: "canceled", active_target_index: null },
      execution: { state: "canceled" }, route: idleRoute,
    });
    await store.refreshNavigationMissionRuntime();
    expect(store.navigationPlan?.path).toEqual([]);
    expect(store.navigationMissionExecution?.state).toBe("canceled");
  });

  it("records a session and exposes the completed file identifier", async () => {
    const store = useAutonomyStore();
    mocks.post.mockResolvedValueOnce({ active: true, session_id: "session", events_written: 0 });
    await store.runRecordingAction("start");
    expect(store.recording?.active).toBe(true);
    expect(mocks.post).toHaveBeenCalledWith("/px/api/autonomy/recordings/start");
    mocks.post.mockResolvedValueOnce({ active: false, session_id: "session", events_written: 123 });
    await store.runRecordingAction("stop");
    expect(store.recording?.active).toBe(false);
    expect(store.recording?.events_written).toBe(123);
    expect(store.recordingLoading).toBe(false);
  });

  it("ignores a runtime poll that predates an operator cancellation", async () => {
    const store = useAutonomyStore();
    let resolvePoll!: (value: unknown) => void;
    mocks.get.mockReturnValueOnce(new Promise((resolve) => { resolvePoll = resolve; }));
    const poll = store.refreshNavigationMissionRuntime();
    mocks.post.mockResolvedValueOnce({ state: "canceled", active_target_index: null });
    await store.runNavigationMissionAction("cancel");
    resolvePoll({ mission: { state: "running" }, execution: {}, route: {} });
    await poll;
    expect(store.navigationMissionExecution?.state).toBe("canceled");
  });

  it("clears a recovered recording status error without hiding an action error", async () => {
    const store = useAutonomyStore();
    store.recordingError = "Could not start";
    store.recordingStatusError = "Network error";
    mocks.get.mockResolvedValueOnce({ active: false, session_id: null });
    await store.refreshRecording();
    expect(store.recordingStatusError).toBeNull();
    expect(store.recordingError).toBe("Could not start");
  });

  it("ignores a recording status poll that started before stop", async () => {
    const store = useAutonomyStore();
    let resolvePoll!: (value: unknown) => void;
    mocks.get.mockReturnValueOnce(new Promise((resolve) => { resolvePoll = resolve; }));
    const poll = store.refreshRecording();
    mocks.post.mockResolvedValueOnce({ active: false, session_id: "session" });
    await store.runRecordingAction("stop");
    resolvePoll({ active: true, session_id: "session" });
    await poll;
    expect(store.recording?.active).toBe(false);
  });

  it("keeps a shared telemetry connection until its last consumer leaves", () => {
    const store = useAutonomyStore();

    store.initialize();
    store.initialize();
    store.cleanup();

    expect(store.consumers).toBe(1);
    expect(mocks.cleanup).not.toHaveBeenCalled();

    store.cleanup();
    expect(store.consumers).toBe(0);
    expect(mocks.cleanup).toHaveBeenCalledOnce();
  });
});
