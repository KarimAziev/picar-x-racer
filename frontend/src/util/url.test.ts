// @vitest-environment jsdom

import { afterEach, describe, expect, it } from "vitest";
import { makeUrl, makeWebsocketUrl } from "@/util/url";

afterEach(() => {
  window.history.replaceState({}, "", "/");
});

describe("URL construction", () => {
  it("does not leak the current route query or fragment into HTTP URLs", () => {
    window.history.replaceState({}, "", "/autonomy?view=map#operator-view");

    const url = new URL(makeUrl("/", 8001));

    expect(url.pathname).toBe("/");
    expect(url.port).toBe("8001");
    expect(url.search).toBe("");
    expect(url.hash).toBe("");
  });

  it("does not leak the current route query or fragment into WebSocket URLs", () => {
    window.history.replaceState({}, "", "/autonomy?view=model#telemetry");

    const url = new URL(makeWebsocketUrl("px/ws", 8001));

    expect(url.protocol).toBe("ws:");
    expect(url.pathname).toBe("/px/ws");
    expect(url.port).toBe("8001");
    expect(url.search).toBe("");
    expect(url.hash).toBe("");
  });
});
