<template>
  <section
    class="rounded-lg border border-blue-300 bg-blue-50 p-4 text-left text-sm text-blue-950 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-100"
    aria-label="Mapping setup"
  >
    <h2 class="font-semibold">Set up mapping</h2>
    <p class="mt-1">
      Mapping needs obstacle distances from LiDAR and movement from the wheels.
      Complete these settings in order.
    </p>
    <ol class="mt-3 space-y-3">
      <li v-for="(step, index) in steps" :key="step.section" class="flex gap-3">
        <span class="mt-1 font-semibold" aria-hidden="true"
          >{{ index + 1 }}.</span
        >
        <div class="min-w-0 flex-1">
          <button
            type="button"
            class="text-left font-semibold underline underline-offset-2 hover:no-underline focus-visible:outline focus-visible:outline-2"
            @click="$emit('open-section', step.section)"
          >
            {{ step.title }}
          </button>
          <span class="ml-2 text-xs">{{
            step.enabled ? "Switched on" : "Switched off"
          }}</span>
          <p class="mt-1 text-xs leading-relaxed">{{ step.description }}</p>
        </div>
      </li>
    </ol>
    <p class="mt-3 text-xs leading-relaxed">
      Save each step before continuing, or save all edited sections together
      with the bottom Save button. Then restart the robot application or reboot
      the Raspberry Pi, return to Autonomy, and start a mapping session.
      Enabling mapping does not start driving.
    </p>
    <details class="mt-3 text-xs">
      <summary class="cursor-pointer font-semibold">
        Using a virtual robot?
      </summary>
      <p class="mt-2 leading-relaxed">
        Configure Motion control and Ackermann odometry with the virtual robot's
        speeds and wheel dimensions. Enable Coherent simulation in the same save
        using the bottom Save button; it supplies wheel readings without
        physical encoders. Enable LiDAR and Local occupancy mapping too.
      </p>
      <button
        type="button"
        class="mt-2 underline"
        @click="$emit('open-section', 'coherent_simulation')"
      >
        Open Coherent simulation
      </button>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Data } from "@/features/settings/stores/robot";

const props = defineProps<{ data: Data }>();
defineEmits<{ "open-section": [section: string] }>();

const steps = computed(() => [
  {
    section: "motion_control",
    title: "Motion control",
    enabled: props.data.motion_control.enabled,
    description:
      "Enter measured maximum forward and reverse speeds in metres per second, then enable Motion control. This also supplies the steering angle needed to calculate turns.",
  },
  {
    section: "localization_sensors",
    title: "Localization sensors → LiDAR sensor and Drive encoders",
    enabled:
      props.data.localization_sensors.lidar.enabled &&
      (props.data.localization_sensors.encoder.enabled ||
        props.data.coherent_simulation.enabled),
    description:
      "Under LiDAR sensor, choose your sensor and enter its minimum and maximum range in metres, then enable it. Under Drive encoders, add the sensors that measure rear-wheel rotation and enable them. An IMU is optional for basic mapping.",
  },
  {
    section: "ackermann_odometry",
    title: "Ackermann odometry",
    enabled: props.data.ackermann_odometry.enabled,
    description:
      "This means tracking movement from wheel turns and steering. Enter the axle spacing, driven-wheel radius, and encoder counts per turn, then enable it. Enter distances in metres: 25 cm = 0.25 m.",
  },
  {
    section: "local_mapping",
    title: "Local occupancy mapping",
    enabled: props.data.local_mapping.enabled,
    description:
      "Enable the top-down obstacle map. The defaults cover 10 × 10 metres with 5 cm squares. You can keep these defaults to start.",
  },
]);
</script>
