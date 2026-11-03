import { isAxiosError } from "axios";
import type { JSONSchema } from "@/ui/JsonSchema/interface";
import { retrieveError, validationErrorPred } from "@/util/error";

/** Display request-validation paths with the labels used by Robot Settings. */
export const robotSettingsError = (
  error: unknown,
  schema: JSONSchema | null,
): string => {
  const detail: unknown = isAxiosError(error)
    ? error.response?.data?.detail
    : null;
  if (!Array.isArray(detail)) return retrieveError(error).text;

  const resolve = (node: JSONSchema): JSONSchema =>
    node.$ref
      ? { ...schema?.$defs?.[node.$ref.split("/").pop()!], ...node }
      : node;
  const child = (input: JSONSchema, part: string | number): JSONSchema => {
    const node = resolve(input);
    if (typeof part === "number") return resolve(node.items ?? {});
    if (node.properties?.[part]) return resolve(node.properties[part]);
    const reference = node.discriminator?.mapping[part];
    if (reference) return resolve({ $ref: reference });
    for (const branch of [...(node.anyOf ?? []), ...(node.oneOf ?? [])]) {
      if (branch.$ref?.split("/").pop() === part) return resolve(branch);
      const found = child(branch, part);
      if (Object.keys(found).length) return found;
    }
    return {};
  };

  return detail
    .map((item) => {
      if (!validationErrorPred(item))
        return "Check the values in Robot Settings.";
      let node = schema ?? {};
      const path = (item.loc as Array<string | number>)
        .filter((part) => part !== "body")
        .map((part) => {
          node = child(node, part);
          return typeof part === "number"
            ? String(part + 1)
            : (node.title ?? part.replaceAll("_", " "));
        })
        .join(" > ");
      const message = String(item.msg).replace(/^Value error, /, "");
      return path ? `${path}: ${message}` : message;
    })
    .join("\n");
};
