from collections.abc import Sequence
from typing import Any, Iterable, List, Optional, Set


def _format_val(v: Any, maxlen=200) -> str:
    s = repr(v)
    if len(s) > maxlen:
        return s[:maxlen] + "...(truncated)"
    return s


def recursive_diff(
    a: Any,
    b: Any,
    path: str = "",
    *,
    max_str_len: int = 200,
    ignore_keys: Optional[Iterable[str]] = None,
) -> List[str]:
    """
    Recursively diff `a` (old) and `b` (new). Returns a list of human-readable
    diff lines describing added/removed/changed values.

    Parameters
    - a, b: values to compare (dicts, sequences, sets, or scalars)
    - path: dotted path to current location (internal use)
    - max_str_len: truncate long reprs for logging
    - ignore_keys: iterable of dict keys to ignore at any level

    Returns List[str] of lines like:
      'added   foo.bar: 123'
      'removed foo.baz: "old"'
      'changed qux[0]: 1 -> 2'
    """
    ignore_set: Set[str] = set(ignore_keys) if ignore_keys is not None else set()
    diffs: List[str] = []

    def p(new: str) -> str:
        return f"{path}.{new}" if path else new

    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(set(a.keys()) | set(b.keys()))
        for k in keys:
            if k in ignore_set:
                continue
            if k not in a:
                diffs.append(f"added   {p(str(k))}: {_format_val(b[k], max_str_len)}")
            elif k not in b:
                diffs.append(f"removed {p(str(k))}: {_format_val(a[k], max_str_len)}")
            else:
                diffs.extend(
                    recursive_diff(
                        a[k],
                        b[k],
                        p(str(k)),
                        max_str_len=max_str_len,
                        ignore_keys=ignore_set,
                    )
                )
        return diffs

    if (
        isinstance(a, Sequence)
        and isinstance(b, Sequence)
        and not isinstance(a, (str, bytes))
        and not isinstance(b, (str, bytes))
    ):
        min_len = min(len(a), len(b))
        for i in range(min_len):
            diffs.extend(
                recursive_diff(
                    a[i],
                    b[i],
                    f"{path}[{i}]",
                    max_str_len=max_str_len,
                    ignore_keys=ignore_set,
                )
            )
        if len(a) < len(b):
            for i in range(min_len, len(b)):
                diffs.append(f"added   {path}[{i}]: {_format_val(b[i], max_str_len)}")
        elif len(a) > len(b):
            for i in range(min_len, len(a)):
                diffs.append(f"removed {path}[{i}]: {_format_val(a[i], max_str_len)}")
        return diffs

    if isinstance(a, set) and isinstance(b, set):
        added = b - a
        removed = a - b
        for v in sorted(added, key=repr):
            diffs.append(f"added   {path}: {_format_val(v, max_str_len)}")
        for v in sorted(removed, key=repr):
            diffs.append(f"removed {path}: {_format_val(v, max_str_len)}")
        return diffs

    if a != b:
        diffs.append(
            f"changed {path}: {_format_val(a, max_str_len)} -> {_format_val(b, max_str_len)}"
        )
    return diffs
