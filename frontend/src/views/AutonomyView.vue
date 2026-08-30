<template>
  <main
    class="h-[var(--app-height)] overflow-y-auto bg-surface-50 p-2 pt-12 text-surface-900 dark:bg-surface-950 dark:text-surface-0 sm:p-3 sm:pt-12"
  >
    <AutonomyStatusBar />

    <div
      class="mt-3 grid min-h-[calc(var(--app-height)-7.25rem)] gap-3 xl:grid-cols-[minmax(0,1fr)_22rem]"
    >
      <section
        class="flex min-h-[34rem] min-w-0 flex-col rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900"
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
            <OccupancyGridPreview v-if="mappingEnabled" />
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
              <OccupancyGridPreview v-if="mappingEnabled" />
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

      <aside class="flex min-w-0 flex-col gap-3">
        <MappingSessionControls />

        <section
          class="rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900"
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <div>
              <h2 class="text-sm font-semibold">Localization runtime</h2>
              <p class="text-[0.68rem] text-surface-500 dark:text-surface-400">
                Acquisition, odometry, and forward safety
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
            <div class="font-semibold">Manual mapping prototype</div>
            <p class="mt-1 leading-relaxed">
              Drive manually to create new observations. Mapping and telemetry
              do not move the vehicle, and no map-based navigation controller is
              installed yet.
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
            Independent mock encoders can report motion while the physical robot
            is stationary. Treat the resulting map as a pipeline demonstration,
            not a physically coherent simulation.
          </div>
        </section>
      </aside>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  autonomyOperatorViewOptions,
  normalizeAutonomyOperatorView,
  type AutonomyOperatorView,
} from "@/features/autonomy";
import { useRobotStore } from "@/features/settings/stores";
import AutonomyStatusBar from "@/features/autonomy/components/AutonomyStatusBar.vue";
import EmptyOperationalView from "@/features/autonomy/components/EmptyOperationalView.vue";
import MappingSessionControls from "@/features/autonomy/components/MappingSessionControls.vue";
import SensorDiagnostics from "@/features/settings/components/robot/SensorDiagnostics.vue";
import OccupancyGridPreview from "@/features/settings/components/robot/OccupancyGridPreview.vue";

const route = useRoute();
const router = useRouter();
const robotStore = useRobotStore();

const currentView = computed(() =>
  normalizeAutonomyOperatorView(route.query.view),
);
const mappingEnabled = computed(() => robotStore.data.local_mapping.enabled);

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
