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
          path_length_m: 0,
          clearance_m: 0.2,
          allow_unknown: false,
          map_sequence: null,
          pose_source: null,
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
          steering_angle_deg: 0,
          cross_track_error_m: 0,
          reason: "Select and review a navigation goal",
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
      path_length_m: 1.41,
      clearance_m: 0.2,
      allow_unknown: false,
      map_sequence: 2,
      pose_source: "localization",
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
      path_length_m: 0,
      clearance_m: 0.2,
      allow_unknown: false,
      map_sequence: null,
      pose_source: null,
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
          path_length_m: 1.26,
          clearance_m: 0.2,
          allow_unknown: false,
          map_sequence: 12,
          pose_source: "localization",
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
        path_length_m: 0,
        clearance_m: 0.2,
        allow_unknown: false,
        map_sequence: null,
        pose_source: null,
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
