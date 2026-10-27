"""A minimal recursive JSON diff for comparing two WCIF snapshots."""

from __future__ import annotations

from typing import Any


def diff(old: Any, new: Any, path: str = "") -> list[str]:
    """Return a human-readable list of changes between two JSON documents."""
    changes: list[str] = []

    if type(old) is not type(new):
        changes.append(f"{path or '(root)'}: {_repr(old)} -> {_repr(new)}")
    elif isinstance(old, dict):
        for key in sorted(set(old) | set(new)):
            sub = f"{path}.{key}" if path else key
            if key not in old:
                changes.append(f"+ {sub}: {_repr(new[key])}")
            elif key not in new:
                changes.append(f"- {sub}: {_repr(old[key])}")
            else:
                changes.extend(diff(old[key], new[key], sub))
    elif isinstance(old, list):
        if len(old) != len(new):
            changes.append(f"{path or '(root)'}: list length {len(old)} -> {len(new)}")
        for i, (a, b) in enumerate(zip(old, new)):
            changes.extend(diff(a, b, f"{path}[{i}]"))
    elif old != new:
        changes.append(f"{path or '(root)'}: {_repr(old)} -> {_repr(new)}")

    return changes


def _repr(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return f"<{type(value).__name__}>"
    return repr(value)
