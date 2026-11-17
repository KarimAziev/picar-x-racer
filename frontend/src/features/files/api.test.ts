// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { downloadFile, downloadFilesAsArchive } from "@/features/files/api";

const { getMock, postMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
}));

vi.mock("@/api", () => ({
  appApi: { get: getMock, post: postMock },
}));

describe("browser downloads", () => {
  const createObjectURL = vi.fn(() => "blob:photo");
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    vi.stubGlobal(
      "URL",
      class extends URL {
        static createObjectURL = createObjectURL;
        static revokeObjectURL = revokeObjectURL;
      },
    );
    getMock.mockResolvedValue(new Blob(["photo"]));
    postMock.mockResolvedValue({
      data: new Blob(["archive"]),
      headers: { "content-disposition": 'attachment; filename="photos.zip"' },
    });
  });

  afterEach(() => {
    vi.runAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    document.body.replaceChildren();
  });

  it.each(["photo", "archive"])(
    "keeps %s downloads out of layout and releases their resources",
    async (kind) => {
      const links: HTMLAnchorElement[] = [];
      vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
        function (this: HTMLAnchorElement) {
          links.push(this);
          expect(this.isConnected).toBe(true);
          expect(this.hidden).toBe(true);
          expect(this.download).toBe(
            kind === "photo" ? "photo.jpg" : "photos.zip",
          );
        },
      );

      for (let index = 0; index < 3; index += 1) {
        if (kind === "photo") {
          await downloadFile("photo.jpg", "image");
        } else {
          await downloadFilesAsArchive(["photo.jpg"], "image");
        }
        expect(document.querySelectorAll("a[download]")).toHaveLength(0);
      }

      expect(links).toHaveLength(3);
      expect(links.every((link) => !link.isConnected)).toBe(true);
      vi.runAllTimers();
      expect(revokeObjectURL).toHaveBeenCalledTimes(3);
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:photo");
    },
  );

  it("cleans up when starting a download fails", async () => {
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {
      throw new Error("Download failed");
    });

    await expect(downloadFile("photo.jpg", "image")).rejects.toThrow(
      "Download failed",
    );

    expect(document.querySelectorAll("a[download]")).toHaveLength(0);
    vi.runAllTimers();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:photo");
  });
});
