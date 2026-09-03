<template>
  <PreloadMask :loading="true" />
  <main
    class="h-[var(--app-height)] overflow-y-auto bg-surface-50 p-2 pt-12 text-surface-900 dark:bg-surface-950 dark:text-surface-0 sm:p-3 sm:pt-12 xl:flex xl:flex-col xl:overflow-hidden"
  >
    <AutonomyStatusBar />

    <div
      class="mt-3 grid min-h-[calc(var(--app-height)-7.25rem)] gap-3 xl:min-h-0 xl:flex-1 xl:grid-cols-[minmax(0,1fr)_22rem]"
    >
      <section
        class="flex min-h-[34rem] min-w-0 flex-col rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900 xl:min-h-0"
      >
        <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 class="text-base font-semibold">Operator view</h1>
            <p class="text-xs text-surface-500 dark:text-surface-400">
              Keyboard and joystick control remain active while Settings is
              closed.
            </p>
          </div>
          <ButtonGroup>
            <Button
              v-for="option in autonomyOperatorViewOptions"
              :key="option.value"
              :label="option.label"
              :icon="option.icon"
              size="small"
              :outlined="currentView !== option.value"
              :severity="currentView === option.value ? 'primary' : 'secondary'"
              :aria-pressed="currentView === option.value"
              @click="selectView(option.value)"
            />
          </ButtonGroup>
        </div>

        <div
          class="relative min-h-0 flex-1 overflow-hidden rounded-lg bg-surface-950"
        >
          <div
            v-if="currentView === 'map'"
            class="h-full min-h-[30rem] overflow-auto p-3"
          >
            <OccupancyGridPreview v-if="mappingEnabled" interactive />
            <EmptyOperationalView
              v-else
              icon="pi pi-map"
              title="Local mapping is disabled"
              description="Enable local mapping in Robot Settings after configuring LiDAR and odometry. Enabling mapping never starts vehicle motion."
            />
          </div>

          <div
            v-else-if="currentView === 'camera'"
            class="relative flex h-full min-h-[30rem] items-center justify-center overflow-hidden"
          >
            <ImageFeed />
          </div>

          <div
            v-else-if="currentView === 'model'"
            class="h-full min-h-[30rem] bg-gradient-to-b from-surface-900 to-surface-950"
          >
            <CarModelViewer
              class="h-full min-h-[30rem]"
              :zoom="10"
              :rotationY="140"
              :rotationX="-5"
            />
            <div
              class="pointer-events-none absolute bottom-3 left-3 rounded-md bg-surface-950/80 px-2 py-1 text-xs text-surface-200"
            >
              Telemetry visualization · not an odometry source
            </div>
          </div>

          <div
            v-else
            class="grid h-full min-h-[30rem] gap-px bg-surface-700 lg:grid-cols-2"
          >
            <div
              class="relative flex min-h-[20rem] items-center overflow-hidden bg-surface-950"
            >
              <ImageFeed />
            </div>
            <div class="min-h-[20rem] overflow-auto bg-surface-950 p-3">
              <OccupancyGridPreview v-if="mappingEnabled" interactive />
              <EmptyOperationalView
                v-else
                icon="pi pi-map"
                title="Local mapping is disabled"
                description="Configure and enable mapping to use the split operator view."
              />
            </div>
          </div>
        </div>
      </section>

      <aside
        class="flex min-w-0 flex-col gap-3 xl:min-h-0 xl:overflow-y-auto xl:overscroll-contain xl:pr-1"
      >
        <SimulationControls />
        <NavigationPlanControls />
        <RelativeMotionControls />
        <MappingSessionControls />

        <section
          class="rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900"
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <div>
              <h2 class="text-sm font-semibold">Localization runtime</h2>
              <p class="text-[0.68rem] text-surface-500 dark:text-surface-400">
                Acquisition, odometry, fusion, and forward safety
              </p>
            </div>
            <Button
              label="Map"
              icon="pi pi-map"
              size="small"
              text
              @click="selectView('map')"
            />
          </div>
          <SensorDiagnostics :show-previews="false" />
        </section>

        <section
          class="rounded-xl border border-surface-200 bg-surface-0 p-3 text-xs shadow-sm dark:border-surface-700 dark:bg-surface-900"
        >
          <h2 class="text-sm font-semibold">Current workflow</h2>
          <div
            class="mt-2 rounded-lg bg-blue-50 p-3 text-blue-900 dark:bg-blue-950 dark:text-blue-100"
          >
            <div class="font-semibold">{{ workflowTitle }}</div>
            <p class="mt-1 leading-relaxed">
              {{ workflowDescription }}
            </p>
          </div>
          <dl class="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5">
            <dt class="text-surface-500">Forward</dt>
            <dd>Use your configured accelerate key</dd>
            <dt class="text-surface-500">Reverse</dt>
            <dd>Use your configured decelerate key</dd>
            <dt class="text-surface-500">Steering</dt>
            <dd>Use your configured left/right keys</dd>
            <dt class="text-surface-500">Stop</dt>
            <dd>Release motion or use the configured stop key</dd>
          </dl>
          <div
            class="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-2 text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
          >
            {{ workflowCaveat }}
          </div>
        </section>
      </aside>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeMount } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  autonomyOperatorViewOptions,
  normalizeAutonomyOperatorView,
  type AutonomyOperatorView,
  useAutonomyStore,
} from "@/features/autonomy";
import { useRobotStore } from "@/features/settings/stores";
import AutonomyStatusBar from "@/features/autonomy/components/AutonomyStatusBar.vue";
import EmptyOperationalView from "@/features/autonomy/components/EmptyOperationalView.vue";
import MappingSessionControls from "@/features/autonomy/components/MappingSessionControls.vue";
import NavigationPlanControls from "@/features/autonomy/components/NavigationPlanControls.vue";
import RelativeMotionControls from "@/features/autonomy/components/RelativeMotionControls.vue";
import SimulationControls from "@/features/autonomy/components/SimulationControls.vue";
import SensorDiagnostics from "@/features/settings/components/robot/SensorDiagnostics.vue";
import OccupancyGridPreview from "@/features/settings/components/robot/OccupancyGridPreview.vue";
import PreloadMask from "@/ui/PreloadMask.vue";

const route = useRoute();
const router = useRouter();
const robotStore = useRobotStore();
const autonomyStore = useAutonomyStore();

onBeforeMount(() => {
  if (!robotStore.loaded) {
    void robotStore.fetchData();
  }
});

const currentView = computed(() =>
  normalizeAutonomyOperatorView(route.query.view),
);
const mappingEnabled = computed(() => robotStore.data.local_mapping.enabled);
const simulationEnabled = computed(
  () =>
    autonomyStore.simulation?.enabled ??
    robotStore.data.coherent_simulation.enabled,
);
const workflowTitle = computed(() =>
  simulationEnabled.value
    ? "Coherent virtual driving"
    : "Manual mapping prototype",
);
const workflowDescription = computed(() =>
  simulationEnabled.value
    ? "Arm manual control, start a bounded relative-motion action, or execute a reviewed map route. The same arbiter drives a virtual Ackermann vehicle while physical motors remain isolated."
    : "Drive manually to create new observations. Mapping and telemetry do not move the vehicle, and no map-based navigation controller is installed yet.",
);
const workflowCaveat = computed(() =>
  simulationEnabled.value
    ? autonomyStore.scanMatching?.enabled
      ? "The known-world matcher now turns LiDAR scans into bounded pose corrections without reading simulator truth. Blue is raw wheel odometry, green is the corrected wheel/gyro estimate, and purple remains truth for evaluation only."
      : "The coherent plant supplies steering, rear encoders, IMU, and world-aware LiDAR. Blue remains raw wheel odometry, green is wheel/gyro pose fusion, and purple is exact simulated truth. Enable simulation scan matching under pose estimation to correct accumulated drift."
    : "Independent mock encoders can report motion while the physical robot is stationary. Treat the resulting map as a pipeline demonstration, not a physically coherent simulation.",
);

const selectView = (view: AutonomyOperatorView) => {
  void router.replace({
    name: "autonomy",
    query: { ...route.query, view },
  });
};

const ImageFeed = defineAsyncComponent({
  loader: () => import("@/ui/ImageFeed.vue"),
});
const CarModelViewer = defineAsyncComponent({
  loader: () =>
    import("@/features/controller/components/CarModelViewer/CarModelViewer.vue"),
});
</script>
