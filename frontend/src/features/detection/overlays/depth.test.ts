import { describe, expect, it } from "vitest";
import { depthPixels } from "./depth";

describe("relative depth palette", () => {
  it("renders near red and far blue", () => {
    const result = depthPixels({ width: 2, height: 1, data: btoa("\x00\xff"), near: 1, far: 5, units: "relative" });
    expect([...result]).toEqual([255, 0, 0, 191, 0, 0, 255, 191]);
  });
  it("rejects mismatched dimensions", () => {
    expect(() => depthPixels({ width: 2, height: 1, data: "", near: 0, far: 0, units: "relative" })).toThrow("dimensions");
  });
});
