// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useMessagerStore } from "@/features/messager";
import { useStore as useRobotStore } from "@/features/settings/stores/robot";

const { patchMock } = vi.hoisted(() => ({
  patchMock: vi.fn(),
}));

vi.mock("@/api", () => ({
  robotApi: {
    patch: patchMock,
  },
}));

describe("robot configuration save feedback", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    patchMock.mockResolvedValue({});
  });

  it("reports a successful hardware-only partial save", async () => {
    const robot = useRobotStore();
    const messager = useMessagerStore();
    const success = vi.spyOn(messager, "success");
    const warning = vi.spyOn(messager, "warning");

    await robot.updatePartialData({ led: { ...robot.data.led, pin: 17 } });

    expect(success).toHaveBeenCalledWith("Robot configuration saved");
    expect(warning).not.toHaveBeenCalled();
  });

  it("reports that startup-scoped autonomy changes require a restart", async () => {
    const robot = useRobotStore();
    const messager = useMessagerStore();
    const success = vi.spyOn(messager, "success");
    const warning = vi.spyOn(messager, "warning");

    await robot.updatePartialData({
      motion_control: {
        ...robot.data.motion_control,
        control_frequency_hz: 25,
      },
    });

    expect(success).toHaveBeenCalledWith("Robot configuration saved");
    expect(warning).toHaveBeenCalledWith(
      "Restart the backend to apply autonomy runtime configuration changes.",
    );
  });
});
