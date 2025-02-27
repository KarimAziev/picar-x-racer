<template>
  <Panel collapsed header="System" toggleable>
    <div class="flex gap-2.5">
      <Restart />
      <Shutdown />
    </div>
  </Panel>
  <Panel header="Camera" toggleable>
    <Fieldset legend="Device" toggleable>
      <VideoDeviceSelect />
    </Fieldset>
    <Fieldset legend="Stream" toggleable>
      <VideoSettings />
    </Fieldset>
  </Panel>
  <Panel header="Appearance" toggleable>
    <SwitchSettings />
  </Panel>
  <Panel header="Theme" toggleable>
    <PrimaryColor />
    <SurfaceColor />
    <DetectionTheme />
  </Panel>
</template>

<script setup lang="ts">
import Panel from "@/ui/Panel.vue";
import { defineAsyncComponent } from "vue";
import SwitchSettings from "@/features/settings/components/general/SwitchSettings.vue";
import PrimaryColor from "@/features/settings/components/theming/PrimaryColor.vue";
import SurfaceColor from "@/features/settings/components/theming/SurfaceColor.vue";
import Skeleton from "@/features/settings/components/general/Skeleton.vue";
import ErrorComponent from "@/ui/ErrorComponent.vue";
import VideoDeviceSelect from "@/features/settings/components/camera/VideoDeviceSelect.vue";
import VideoSettings from "@/features/settings/components/camera/VideoSettings.vue";

const DetectionTheme = defineAsyncComponent({
  loader: () =>
    import("@/features/settings/components/theming/DetectionTheme.vue"),
  loadingComponent: Skeleton,
  delay: 0,
  errorComponent: ErrorComponent,
});

/**
 * const VideoSettings = defineAsyncComponent({
 *   loader: () =>
 *     import("@/features/settings/components/camera/VideoSettings.vue"),
 *   loadingComponent: Skeleton,
 *   delay: 0,
 *   errorComponent: ErrorComponent,
 * });
 */

/**
 * const VideoDeviceSelect = defineAsyncComponent({
 *   loader: () =>
 *     import("@/features/settings/components/camera/VideoDeviceSelect.vue"),
 *   loadingComponent: Skeleton,
 *   delay: 0,
 *   errorComponent: ErrorComponent,
 * });
 */

const Shutdown = defineAsyncComponent({
  loader: () => import("@/features/settings/components/system/Shutdown.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const Restart = defineAsyncComponent({
  loader: () => import("@/features/settings/components/system/Restart.vue"),
  loadingComponent: Skeleton,
  delay: 0,
  errorComponent: ErrorComponent,
});
</script>
