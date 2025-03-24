import mimetypes
from pathlib import Path
from typing import Optional

text_extensions = {
    ".param",
    ".html",
    ".htm",
    ".xml",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".csv",
    ".ini",
    ".cfg",
    ".conf",
    ".properties",
    ".py",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".js",
    ".cjs",
    ".ts",
    ".jsx",
    ".tsx",
    ".rb",
    ".php",
    ".pl",
    ".go",
    ".swift",
    ".kt",
    ".scala",
    ".rs",
    ".sh",
    ".bat",
    ".ps1",
    ".r",
    ".m",
    ".jl",
    ".css",
    ".scss",
    ".less",
    ".vue",
    ".svelte",
    ".tmpl",
    ".tpl",
    ".md",
    ".markdown",
    ".txt",
    ".org",
    ".log",
    ".logs",
    ".dockerfile",
}


def guess_mime_type(filename: str) -> Optional[str]:
    filepath = Path(filename)
    extension = filepath.suffix

    content_type = (
        "text/plain"
        if (not extension and not filepath.is_dir()) or extension in text_extensions
        else None
    )

    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)

    return content_type
