// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useWebSocket } from "@/composables/useWebsocket";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  binaryType: BinaryType = "blob";
  onclose: (() => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onopen: (() => void | Promise<void>) | null = null;
  sent: string[] = [];

  constructor(public readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  close() {}

  send(message: string) {
    this.sent.push(message);
  }

  async open() {
    await this.onopen?.();
  }
}

describe("useWebSocket disconnected message handling", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("drops disconnected commands when replay is disabled", async () => {
    const model = useWebSocket({
      url: "px/ws",
      port: 8001,
      queueMessages: false,
    });
    model.initWS();
    const socket = FakeWebSocket.instances[0];

    model.send({ action: "move", payload: { direction: 1, speed: 80 } });
    await socket.open();

    expect(socket.sent).toEqual([]);
  });

  it("retains queueing by default for non-control sockets", async () => {
    const model = useWebSocket({ url: "sync/ws", port: 8000 });
    model.initWS();
    const socket = FakeWebSocket.instances[0];

    model.send({ action: "sync" });
    await socket.open();

    expect(socket.sent).toEqual([JSON.stringify({ action: "sync" })]);
  });
});
