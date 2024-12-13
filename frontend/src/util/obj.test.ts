import { describe, it, expect } from "vitest";
import { diffObjectsDeep } from "@/util/obj";

describe("diffObjectsDeep", () => {
  it("should return undefined for identical objects", () => {
    const orig = { a: 1, b: 2 };
    const updated = { a: 1, b: 2 };
    expect(diffObjectsDeep(orig, updated)).toBeUndefined();
  });

  it("should return differences for primitive changes", () => {
    const orig = { a: 1, b: "hello" };
    const updated = { a: 2, b: "world" };
    expect(diffObjectsDeep(orig, updated)).toEqual({ a: 2, b: "world" });
  });

  it("should detect added keys", () => {
    const orig = { a: 1 };
    const updated = { a: 1, b: 2 };
    expect(diffObjectsDeep(orig, updated)).toEqual({ b: 2 });
  });

  it("should detect removed keys", () => {
    const orig = { a: 1, b: 2 };
    const updated = { a: 1 };

    expect(diffObjectsDeep(orig, updated)).toEqual({ b: undefined });
  });

  it("should handle nested objects", () => {
    const orig = { a: 1, nested: { b: 2, c: 3 } };
    const updated = { a: 1, nested: { b: 2, c: 4 } };
    expect(diffObjectsDeep(orig, updated)).toEqual({ nested: { c: 4 } });
  });
  it("should handle very deeply nested objects", () => {
    const orig = { a: 1, nested: { veryNested: [{ c: 3 }, { b: 2, c: 3 }] } };
    const updated = {
      a: 1,
      nested: { veryNested: [{ b: 2, c: 3 }, { b: 2 }] },
    };

    expect(diffObjectsDeep(orig, updated)).toEqual({
      nested: { veryNested: [{ b: 2 }, { c: undefined }] },
    });
  });

  it("should handle arrays of objects", () => {
    const orig = [{ c: 3 }, { b: 2, c: 3 }];
    const updated = [{ b: 2, c: 3 }, { b: 2 }];

    expect(diffObjectsDeep(orig, updated)).toEqual([
      { b: 2 },
      { c: undefined },
    ]);
  });

  it("should handle arrays with added elements", () => {
    const orig = [1, 2, 3];
    const updated = [1, 2, 3, 4];
    expect(diffObjectsDeep(orig, updated)).toEqual([4]);
  });

  it("should handle arrays with removed elements", () => {
    const orig = [1, 2, 3];
    const updated = [1, 2];
    expect(diffObjectsDeep(orig, updated)).toEqual([1, 2]);
  });

  it("should handle deeply nested objects and arrays", () => {
    const orig = { a: [1, { b: 2 }] };
    const updated = { a: [1, { b: 3 }] };
    expect(diffObjectsDeep(orig, updated)).toEqual({ a: [{ b: 3 }] });
  });

  it("should handle circular references gracefully", () => {
    const orig: any = { a: 1 };
    orig.circular = orig;

    const updated: any = { a: 2 };
    updated.circular = updated;

    expect(diffObjectsDeep(orig, updated)).toEqual({ a: 2 });
  });

  it("should handle new array insertion at an index", () => {
    const orig = [1, 2, 3];
    const updated = [1, 99, 2, 3];
    expect(diffObjectsDeep(orig, updated)).toEqual([99]);
  });

  it("should return undefined for completely empty input", () => {
    const orig = {};
    const updated = {};
    expect(diffObjectsDeep(orig, updated)).toBeUndefined();
  });
});
