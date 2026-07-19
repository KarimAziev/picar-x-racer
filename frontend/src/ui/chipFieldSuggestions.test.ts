import { describe, expect, it } from "vitest";
import { filterChipSuggestions } from "@/ui/chipFieldSuggestions";

describe("filterChipSuggestions", () => {
  it("filters case-insensitively and excludes selected labels", () => {
    expect(
      filterChipSuggestions(["person", "sports ball", "car"], ["person"], "SP"),
    ).toEqual(["SP", "sports ball"]);
  });

  it("offers an unmatched query as a custom label", () => {
    expect(filterChipSuggestions(["person", "car"], [], "robot")).toEqual([
      "robot",
    ]);
  });

  it("shows available labels when focused with an empty query", () => {
    expect(filterChipSuggestions(["person", "car"], ["car"], "")).toEqual([
      "person",
    ]);
  });

  it("puts a canonical exact match before partial matches", () => {
    expect(
      filterChipSuggestions(
        ["sports ball", "Ball", "baseball bat"],
        [],
        "ball",
      ),
    ).toEqual(["Ball", "sports ball", "baseball bat"]);
  });

  it("deduplicates suggestions case-insensitively", () => {
    expect(filterChipSuggestions(["person", "PERSON"], [], "")).toEqual([
      "person",
    ]);
  });
});
