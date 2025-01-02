<template>
  <Panel collapsed header="System" toggleable>
    <div class="flex gap-2.5">
      <Restart />
      <Shutdown />
    </div>
  </Panel>
  <Panel header="Appearance" toggleable>
    <SwitchSettings />
    <div class="flex">
      <div class="flex-1">
        <FPSToggle />
      </div>
      <div class="flex-1">
        <DarkThemeSwitch />
      </div>
    </div>
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
import Music from "@/features/settings/components/general/Music.vue";
import SwitchSettings from "@/features/settings/components/general/SwitchSettings.vue";
import VideoSettings from "@/features/settings/components/camera/VideoSettings.vue";
import Panel from "@/ui/Panel.vue";
import FPSToggle from "@/features/settings/components/camera/FPSToggle.vue";
import VideoDeviceSelect from "@/features/settings/components/camera/VideoDeviceSelect.vue";
import BatterySettings from "@/features/settings/components/general/BatterySettings.vue";
import Shutdown from "@/features/settings/components/system/Shutdown.vue";
import Restart from "@/features/settings/components/system/Restart.vue";
import RobotSettings from "@/features/settings/components/robot/RobotSettings.vue";
import PrimaryColor from "@/features/settings/components/theming/PrimaryColor.vue";
import SurfaceColor from "@/features/settings/components/theming/SurfaceColor.vue";

import DarkThemeSwitch from "@/features/settings/components/theming/DarkThemeSwitch.vue";
</script>
