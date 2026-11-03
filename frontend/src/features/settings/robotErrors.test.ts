import { describe, expect, it } from "vitest";
import { robotSettingsError } from "./robotErrors";

const errorWithDetail = (detail: unknown) => ({
  isAxiosError: true,
  response: { data: { detail } },
});

describe("robot settings validation feedback", () => {
  it("uses form labels and units for nested request errors", () => {
    const message = robotSettingsError(
      errorWithDetail([
        {
          loc: ["body", "local_mapping", "width_m"],
          msg: "Input should be greater than 1",
          type: "greater_than",
        },
      ]),
      {
        properties: {
          local_mapping: {
            title: "Local occupancy mapping",
            $ref: "#/$defs/LocalMappingConfig",
          },
        },
        $defs: {
          LocalMappingConfig: {
            properties: { width_m: { title: "Map width (m)" } },
          },
        },
      },
    );
    expect(message).toBe(
      "Local occupancy mapping > Map width (m): Input should be greater than 1",
    );
  });

  it("preserves actionable dependency errors without a validator prefix", () => {
    expect(
      robotSettingsError(
        errorWithDetail([
          {
            loc: ["body"],
            msg: "Value error, Enable Robot > Motion control.",
            type: "value_error",
          },
        ]),
        null,
      ),
    ).toBe("Enable Robot > Motion control.");
  });

  it("preserves merge errors and network failures", () => {
    expect(
      robotSettingsError(
        errorWithDetail("Enable Robot > Motion control."),
        null,
      ),
    ).toBe("Enable Robot > Motion control.");
    expect(robotSettingsError(new Error("Connection lost"), null)).toBe(
      "Connection lost",
    );
  });
});

it("distinguishes fields with the same name in different sections", () => {
  expect(
    robotSettingsError(
      errorWithDetail([
        {
          loc: ["body", "motion_control", "command_timeout_ms"],
          msg: "Too small",
          type: "greater_than",
        },
      ]),
      {
        properties: {
          motion_control: { title: "Motion control", $ref: "#/$defs/Motion" },
          coherent_simulation: {
            title: "Coherent simulation",
            $ref: "#/$defs/Simulation",
          },
        },
        $defs: {
          Simulation: {
            properties: {
              command_timeout_ms: { title: "Simulation command timeout (ms)" },
            },
          },
          Motion: {
            properties: {
              command_timeout_ms: { title: "Command timeout (ms)" },
            },
          },
        },
      },
    ),
  ).toBe("Motion control > Command timeout (ms): Too small");
});
