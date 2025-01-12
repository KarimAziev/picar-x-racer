from typing import Optional, Type

from pydantic import BaseModel


def build_response_description(
    schema: Type[BaseModel], title: Optional[str] = None
) -> str:
    """
    Generate a `response_description` string programmatically
    from the descriptions of fields in a Pydantic schema.

    Args:
        schema: The Pydantic model to extract field descriptions from.
        title: A custom title to include as the first line of the response description, if provided.

    Returns:
        str: A formatted response description based on the schema field descriptions.
    """
    if title is None:
        title_lines = extract_clean_docstring(schema).splitlines()
        title = next(iter(title_lines), None)

    lines = [title] if title else []
    for field_name, field_info in schema.model_fields.items():
        if field_info.description:
            description_lines = field_info.description.splitlines()

            lines.append(f"- **{field_name}**: {description_lines[0]}")

            for line in description_lines[1:]:
                if line.strip().startswith(("-", "*")):
                    lines.append(f"  {line.strip()}")
                else:
                    lines.append(f"  {line.strip()}")
    return "\n".join(lines)


def extract_clean_docstring(obj: type | object) -> str:
    """
    Extract and clean up the __doc__ string from a class, object, or enum.

    Args:
        obj: The object or class from which to extract the docstring.

    Returns:
        str: A cleaned, whitespace-trimmed docstring, or an empty string if no docstring is found.
    """
    doc = getattr(obj, "__doc__", "")
    if not doc:
        return ""
    return "\n".join(line.strip() for line in doc.splitlines() if line.strip())
