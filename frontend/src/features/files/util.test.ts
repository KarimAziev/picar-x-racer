import { describe, expect, it } from "vitest";
import type { BatchFileStatus } from "@/features/files/interface";
import {
  bytesToSize,
  expandFileName,
  extractContentDispositionFilename,
  getBatchFilesErrorMessage,
  isDateFilter,
  isPlainFilter,
  mapChildren,
  mapConcat,
  type ItemData,
} from "@/features/files/util";

describe("bytesToSize", () => {
  it.each([
    [0, undefined, "0 B"],
    [999, undefined, "999 B"],
    [1_000, undefined, "1.0 KB"],
    [1_250_000, 2, "1.25 MB"],
    [1_000_000_000, 0, "1 GB"],
  ])("formats %i bytes", (bytes, decimals, expected) => {
    expect(bytesToSize(bytes, decimals)).toBe(expected);
  });

  it("returns null when the size exceeds the supported units", () => {
    expect(bytesToSize(1_000 ** 8)).toBeNull();
  });
});

describe("getBatchFilesErrorMessage", () => {
  const status = (filename: string, success: boolean): BatchFileStatus => ({
    filename,
    success,
    error: success ? null : "operation failed",
  });

  it("returns undefined when every operation succeeds", () => {
    expect(
      getBatchFilesErrorMessage(
        [status("first.txt", true), status("second.txt", true)],
        "delete",
      ),
    ).toBeUndefined();
  });

  it("reports all failed filenames", () => {
    expect(
      getBatchFilesErrorMessage(
        [status("first.txt", false), status("second.txt", false)],
        "delete",
      ),
    ).toEqual({
      error: "first.txt, second.txt",
      title: "Failed to delete: ",
    });
  });

  it("uses the partial-failure title when some operations succeed", () => {
    expect(
      getBatchFilesErrorMessage(
        [
          status("kept.txt", true),
          status("first.txt", false),
          status("second.txt", false),
        ],
        "move",
      ),
    ).toEqual({
      error: "first.txt, second.txt",
      title: "Failed to move some files: ",
    });
  });
});

describe("extractContentDispositionFilename", () => {
  it.each([
    ["attachment; filename=photo.jpg", "photo.jpg"],
    ['attachment; filename="photo%20one.jpg"', "photo one.jpg"],
    ["attachment; filename*=UTF-8''report%20final.pdf", "report final.pdf"],
  ])("extracts a filename from %s", (header, expected) => {
    expect(extractContentDispositionFilename(header)).toBe(expected);
  });

  it.each([undefined, "attachment", "inline; name=file.txt"])(
    "returns undefined when no filename is present",
    (header) => {
      expect(extractContentDispositionFilename(header)).toBeUndefined();
    },
  );
});

describe("mapChildren", () => {
  it("maps a tree in depth-first order and marks only leaves selectable", () => {
    const items: ItemData<{ label: string }>[] = [
      {
        key: "directory",
        label: "Directory",
        children: [
          { key: "nested-file", label: "Nested file" },
          {
            key: "nested-directory",
            label: "Nested directory",
            children: [{ key: "deep-file", label: "Deep file" }],
          },
        ],
      },
      { key: "root-file", label: "Root file" },
    ];

    expect(mapChildren(items)).toEqual([
      {
        key: "directory",
        label: "Directory",
        tabIdx: 1,
        selectable: false,
        children: [
          {
            key: "nested-file",
            label: "Nested file",
            tabIdx: 2,
            selectable: true,
          },
          {
            key: "nested-directory",
            label: "Nested directory",
            tabIdx: 3,
            selectable: false,
            children: [
              {
                key: "deep-file",
                label: "Deep file",
                tabIdx: 4,
                selectable: true,
              },
            ],
          },
        ],
      },
      {
        key: "root-file",
        label: "Root file",
        tabIdx: 5,
        selectable: true,
      },
    ]);
  });

  it("starts indexing from the supplied counter", () => {
    expect(mapChildren([{ key: "file", label: "File" }], { value: 7 })).toEqual(
      [
        {
          key: "file",
          label: "File",
          tabIdx: 7,
          selectable: true,
        },
      ],
    );
  });
});

describe("filter guards", () => {
  it.each([
    [{ match_mode: "in", value: ["image"] }, true],
    [{ match_mode: "", value: [] }, false],
    [{ value: ["image"] }, false],
    [null, false],
    [[], false],
  ])("identifies plain filters", (filter, expected) => {
    expect(Boolean(isPlainFilter(filter))).toBe(expected);
  });

  it.each([
    [{ constraints: [], operator: null, value: null }, true],
    [{ constraints: "not-an-array" }, false],
    [{ operator: null, value: null }, false],
    [null, false],
    [[], false],
  ])("identifies date filters", (filter, expected) => {
    expect(isDateFilter(filter)).toBe(expected);
  });
});

describe("mapConcat", () => {
  it("removes empty values and joins the remaining strings", () => {
    expect(mapConcat(["alpha", null, "", undefined, "beta"], "/")).toBe(
      "alpha/beta",
    );
  });

  it("uses an empty separator by default", () => {
    expect(mapConcat(["a", "b", "c"])).toBe("abc");
  });
});

describe("expandFileName", () => {
  it("filters empty path segments", () => {
    const result = expandFileName(
      "myfile.txt",
      "/root",
      null,
      "",
      "home",
      undefined,
      "user",
    );

    expect(result).toBe("/root/home/user/myfile.txt");
  });

  it("returns the filename when no directories are provided", () => {
    expect(expandFileName("myfile.txt")).toBe("myfile.txt");
  });
});
