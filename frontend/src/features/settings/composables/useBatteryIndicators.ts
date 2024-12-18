import { computed } from "vue";
import { useSettingsStore, useBatteryStore } from "@/features/settings/stores";
import { roundNumber } from "@/util/number";

export const useBatteryIndicators = () => {
  const batteryStore = useBatteryStore();
  const settingsStore = useSettingsStore();

  const batteryVoltage = computed(() => `${batteryStore.voltage || 0}V`);

  const percentage = computed(() => {
    const value = roundNumber(
      batteryStore.voltage - settingsStore.data.battery.min_voltage,
      2,
    );
    const total = roundNumber(
      settingsStore.data.battery.full_voltage -
        settingsStore.data.battery.min_voltage,
      2,
    );
    return roundNumber(Math.max(0, value / total) * 100, 1);
  });

  const className = computed(() => {
    const voltage = batteryStore.voltage;

    if (voltage >= settingsStore.data.battery.warn_voltage) {
      return "color-primary";
    } else if (
      voltage < settingsStore.data.battery.warn_voltage &&
      voltage > settingsStore.data.battery.danger_voltage
    ) {
      return "color-warning";
    } else {
      return "color-error blink";
    }
  });

  return {
    batteryVoltage,
    percentage,
    className,
  };
};
