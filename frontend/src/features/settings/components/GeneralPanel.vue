<template>
  <Panel collapsed header="System" toggleable>
    <div class="flex gap-2.5">
      <Restart />
      <Shutdown />
    </div>
  </Panel>
  <Panel header="Appearance" toggleable>
    <SwitchSettings />
    <PrimaryColor />
    <SurfaceColor />
  </Panel>

  <Panel header="Camera" toggleable>
    <div class="wrapper">
      <div class="column">
        <VideoSettings />
      </div>
      <div class="column">
        <Fieldset legend="Device settings">
          <VideoDeviceSelect />
        </Fieldset>
      </div>
    </div>
  </Panel>
  <Panel collapsed header="Robot" toggleable>
    <RobotSettings />
  </Panel>
  <Panel collapsed header="Battery" toggleable>
    <BatterySettings />
  </Panel>
  <Panel collapsed header="Music" toggleable>
    <Music />
  </Panel>
</template>

<script setup lang="ts">
import Panel from "@/ui/Panel.vue";
import { defineAsyncComponent } from "vue";
import ProgressSpinner from "primevue/progressspinner";
import SwitchSettings from "@/features/settings/components/general/SwitchSettings.vue";
import PrimaryColor from "@/features/settings/components/theming/PrimaryColor.vue";
import SurfaceColor from "@/features/settings/components/theming/SurfaceColor.vue";

const Music = defineAsyncComponent({
  loader: () => import("@/features/settings/components/general/Music.vue"),
  loadingComponent: ProgressSpinner,
  delay: 0,
});

const VideoSettings = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/camera/VideoSettings.vue"),
  loadingComponent: ProgressSpinner,
  delay: 0,
});

const VideoDeviceSelect = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/camera/VideoDeviceSelect.vue"),
  loadingComponent: ProgressSpinner,
  delay: 0,
});

const BatterySettings = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/general/BatterySettings.vue"),
  loadingComponent: ProgressSpinner,
  delay: 0,
});

const Shutdown = defineAsyncComponent({
  loader: () => import("@/features/settings/components/system/Shutdown.vue"),
  loadingComponent: ProgressSpinner,
  delay: 0,
});

const Restart = defineAsyncComponent({
  loader: () => import("@/features/settings/components/system/Restart.vue"),
  loadingComponent: ProgressSpinner,
  delay: 0,
});

const RobotSettings = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/robot/RobotSettings.vue"),
  loadingComponent: ProgressSpinner,
  delay: 0,
});

/**
 * const PrimaryColor = defineAsyncComponent({
 *   loader: () =>
 *     import("@/features/settings/components/theming/PrimaryColor.vue"),
 *   loadingComponent: ProgressSpinner,
 *   delay: 0,
 * });
 *
 * const SurfaceColor = defineAsyncComponent({
 *   loader: () =>
 *     import("@/features/settings/components/theming/SurfaceColor.vue"),
 *   loadingComponent: ProgressSpinner,
 *   delay: 0,
 * });
 */
</script>
