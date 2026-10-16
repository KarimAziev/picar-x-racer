import type { JSONSchema } from "@/ui/JsonSchema/interface";
import { detectCandidateIndex, resolveRef } from "@/ui/JsonSchema/util";
import { isPlainObject } from "@/util/guards";
import { startCase } from "@/util/str";

export type PinAssignmentState = "enabled" | "disabled" | "configured";

export interface PinAssignment {
  key: string;
  owner: string;
  field: string;
  value: string | number;
  state: PinAssignmentState;
}

/** Collect physical GPIO fields from the same schema branches as the form. */
export function collectPinAssignments(
  schema: JSONSchema | null,
  model: unknown,
): PinAssignment[] {
  const assignments: PinAssignment[] = [];
  const defs = schema?.$defs;

  function visit(
    rawSchema: JSONSchema,
    value: unknown,
    path: (string | number)[],
    owners: string[],
    state: PinAssignmentState,
    itemLabel?: string,
  ) {
    if (value === null || value === undefined) {
      return;
    }
    const resolved = resolveRef(rawSchema, defs) || rawSchema;
    if (resolved["x-ui-type"] === "pin") {
      if (typeof value === "string" || typeof value === "number") {
        assignments.push({
          key: JSON.stringify(path),
          owner: owners.join(" · "),
          field: resolved.title || startCase(String(path.at(-1))),
          value,
          state,
        });
      }
      return;
    }

    const branches = resolved.anyOf || resolved.oneOf;
    if (branches && isPlainObject(value)) {
      const options = branches.map(
        (branch) => resolveRef(branch, defs) || branch,
      );
      const selected =
        options[detectCandidateIndex(value, options, resolved, defs)];
      if (selected) {
        visit(
          { ...selected, title: resolved.title || selected.title },
          value,
          path,
          owners,
          state,
          itemLabel,
        );
      }
      return;
    }

    if (Array.isArray(value) && resolved.items) {
      const label = resolved.title || startCase(String(path.at(-1)));
      const items = resolved.items;
      value.forEach((item, index) => {
        visit(
          items,
          item,
          [...path, index],
          [...owners, label],
          state,
          `${resolved.props?.itemLabel || "Item"} ${index + 1}`,
        );
      });
      return;
    }

    if (isPlainObject(value) && resolved.properties) {
      const name = typeof value.name === "string" ? value.name.trim() : "";
      const owner =
        name || itemLabel || resolved.title || startCase(String(path.at(-1)));
      const nextOwners = path.length ? [...owners, owner] : owners;
      const nextState =
        state === "disabled" || value.enabled === false
          ? "disabled"
          : value.enabled === true
            ? "enabled"
            : state;
      Object.entries(resolved.properties).forEach(([key, property]) => {
        visit(property, value[key], [...path, key], nextOwners, nextState);
      });
    }
  }

  if (schema) {
    visit(schema, model, [], [], "configured");
  }
  return assignments;
}
