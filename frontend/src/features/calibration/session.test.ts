import { beforeEach, describe, expect, it, vi } from "vitest";
import { CalibrationLease, type CalibrationStatus } from "./session";
const { post } = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("@/api", () => ({ robotApi: { post } }));
const active = { active: true, session_id: "session" } as CalibrationStatus;
beforeEach(() => {
  post.mockReset();
});
describe("calibration hold lease", () => {
  it("sends release immediately even if a drive request is in flight", async () => {
    let resolveDrive!: (value: CalibrationStatus) => void;
    post
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveDrive = resolve;
          }),
      )
      .mockResolvedValue(active);
    const update = vi.fn(),
      failed = vi.fn();
    const lease = new CalibrationLease("session", update, failed);
    lease.hold();
    await lease.release();
    expect(post.mock.calls[0][1]).toMatchObject({ sequence: 1, drive: true });
    expect(post.mock.calls[1][1]).toMatchObject({ sequence: 2, drive: false });
    resolveDrive({ ...active, driving: true });
    await Promise.resolve();
    expect(update).toHaveBeenCalledTimes(1);
    expect(failed).not.toHaveBeenCalled();
  });
  it("stops renewing a lease after a network failure and requests cancellation", async () => {
    post.mockRejectedValue(new Error("offline"));
    const failed = vi.fn();
    const lease = new CalibrationLease("session", vi.fn(), failed);
    await lease.heartbeat();
    expect(failed).toHaveBeenCalledOnce();
    expect(post).toHaveBeenLastCalledWith("px/api/calibration/session/cancel");
    await lease.heartbeat();
    lease.hold();
    expect(post).toHaveBeenCalledTimes(2);
  });
  it("does not send overlapping periodic requests", async () => {
    post.mockReturnValue(new Promise(() => {}));
    const lease = new CalibrationLease("session", vi.fn(), vi.fn());
    void lease.heartbeat();
    void lease.heartbeat();
    expect(post).toHaveBeenCalledOnce();
    lease.close();
  });
  it("ignores responses after the guide closes", async () => {
    let respond!: (value: CalibrationStatus) => void;
    post.mockImplementation(
      () =>
        new Promise((resolve) => {
          respond = resolve;
        }),
    );
    const update = vi.fn();
    const lease = new CalibrationLease("session", update, vi.fn());
    const pending = lease.heartbeat();
    lease.close();
    respond(active);
    await pending;
    expect(update).not.toHaveBeenCalled();
  });
  it("does not resume a session that the robot ended", async () => {
    post.mockResolvedValue({ ...active, active: false, session_id: null });
    const lease = new CalibrationLease("session", vi.fn(), vi.fn());
    await lease.heartbeat();
    lease.hold();
    await lease.heartbeat();
    expect(post).toHaveBeenCalledOnce();
  });
});
