export const autonomyOperatorViews = [
  "map",
  "split",
  "camera",
  "model",
] as const;

export type AutonomyOperatorView = (typeof autonomyOperatorViews)[number];

export const normalizeAutonomyOperatorView = (
  value: unknown,
): AutonomyOperatorView =>
  typeof value === "string" &&
  autonomyOperatorViews.includes(value as AutonomyOperatorView)
    ? (value as AutonomyOperatorView)
    : "map";

export const autonomyOperatorViewOptions: ReadonlyArray<{
  value: AutonomyOperatorView;
  label: string;
  icon: string;
}> = [
  { value: "map", label: "Map", icon: "pi pi-map" },
  { value: "split", label: "Split", icon: "pi pi-th-large" },
  { value: "camera", label: "Camera", icon: "pi pi-video" },
  { value: "model", label: "3D", icon: "pi pi-box" },
];
