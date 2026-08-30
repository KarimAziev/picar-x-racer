import { describe, expect, it } from "vitest";
import { normalizeAutonomyOperatorView } from "@/features/autonomy/operatorView";

describe("autonomy operator view", () => {
  it.each(["map", "split", "camera", "model"])(
    "accepts the %s view",
    (view) => {
      expect(normalizeAutonomyOperatorView(view)).toBe(view);
    },
  );

  it.each([undefined, null, "", "unknown", ["model"]])(
    "uses the map for an unsupported query value",
    (view) => {
      expect(normalizeAutonomyOperatorView(view)).toBe("map");
    },
  );
});
