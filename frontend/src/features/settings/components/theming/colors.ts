import { preset as Robo } from "@/presets/RoboPreset";

export type ColorOption = {
  value: string;
  label: string;
};

export const colorOptions: ColorOption[] = [
  { label: "robo", value: Robo.semantic.primary[500] },
  {
    label: "emerald",
    value: "#10b981",
  },
  {
    label: "green",
    value: "#22c55e",
  },
  {
    label: "lime",
    value: "#84cc16",
  },
  {
    label: "orange",
    value: "#f97316",
  },
  {
    label: "amber",
    value: "#f59e0b",
  },
  {
    label: "yellow",
    value: "#eab308",
  },
  {
    label: "teal",
    value: "#14b8a6",
  },
  {
    label: "cyan",
    value: "#06b6d4",
  },
  {
    label: "sky",
    value: "#0ea5e9",
  },
  {
    label: "blue",
    value: "#3b82f6",
  },
  {
    label: "indigo",
    value: "#6366f1",
  },
  {
    label: "violet",
    value: "#8b5cf6",
  },
  {
    label: "purple",
    value: "#a855f7",
  },
  {
    label: "fuchsia",
    value: "#d946ef",
  },
  {
    label: "pink",
    value: "#ec4899",
  },
  {
    label: "rose",
    value: "#f43f5e",
  },
];
