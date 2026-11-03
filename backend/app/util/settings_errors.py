"""Readable validation messages for the schema-driven robot settings form."""

from typing import Any

from pydantic import ValidationError


def format_settings_errors(error: ValidationError, schema: dict[str, Any]) -> str:
    """Use form labels for field paths without exposing input dumps or URLs."""
    definitions = schema.get("$defs", {})

    def resolve(node: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in node:
            return {**definitions.get(node["$ref"].split("/")[-1], {}), **node}
        return node

    def child(node: dict[str, Any], part: str | int) -> dict[str, Any]:
        node = resolve(node)
        if isinstance(part, int):
            return resolve(node.get("items", {}))
        if part in node.get("properties", {}):
            return resolve(node["properties"][part])
        mapping = node.get("discriminator", {}).get("mapping", {})
        if part in mapping:
            return resolve({"$ref": mapping[part]})
        for branch in node.get("anyOf", []) + node.get("oneOf", []):
            if branch.get("$ref", "").split("/")[-1] == part:
                return resolve(branch)
            found = child(branch, part)
            if found:
                return found
        return {}

    messages = []
    for item in error.errors(
        include_url=False, include_context=False, include_input=False
    ):
        node = schema
        labels = []
        for part in item["loc"]:
            node = child(node, part)
            labels.append(
                str(part + 1)
                if isinstance(part, int)
                else node.get("title", part.replace("_", " "))
            )
        path = " > ".join(labels)
        message = item["msg"].removeprefix("Value error, ")
        messages.append(f"{path}: {message}" if path else message)
    return "\n".join(messages)
