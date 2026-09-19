#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "architecture" / "manifest.json"

sys.path.insert(0, str(ROOT))
from host.hil.core import Capability  # noqa: E402


def main() -> int:
    errors: list[str] = []

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"architecture-check: cannot read {MANIFEST}: {exc}", file=sys.stderr)
        return 1

    if manifest.get("schema_version") != 2:
        errors.append("architecture/manifest.json schema_version must be 2")

    required_paths = manifest.get("required_paths")
    if not isinstance(required_paths, list):
        errors.append("required_paths must be a list")
        required_paths = []

    for relative in required_paths:
        if not isinstance(relative, str):
            errors.append(f"non-string required path: {relative!r}")
            continue
        if not (ROOT / relative).exists():
            errors.append(f"missing required architecture path: {relative}")

    roles = manifest.get("board_roles", {})
    if not isinstance(roles, dict):
        errors.append("board_roles must be an object")
    else:
        for path, role in roles.items():
            if not (ROOT / path).exists():
                errors.append(f"board role points to missing path: {path} ({role})")

    declared = manifest.get("backend_capabilities")
    if not isinstance(declared, list) or not all(isinstance(v, str) for v in declared):
        errors.append("backend_capabilities must be a list of strings")
        declared_set: set[str] = set()
    else:
        declared_set = set(declared)
        if len(declared_set) != len(declared):
            errors.append("backend_capabilities contains duplicates")

    code_set = {item.value for item in Capability}
    missing_in_manifest = sorted(code_set - declared_set)
    missing_in_code = sorted(declared_set - code_set)
    if missing_in_manifest:
        errors.append(
            "capabilities implemented in host API but missing from manifest: "
            + ", ".join(missing_in_manifest)
        )
    if missing_in_code:
        errors.append(
            "capabilities declared in manifest but missing from host API: "
            + ", ".join(missing_in_code)
        )

    services = manifest.get("controller_services")
    if not isinstance(services, list) or not services:
        errors.append("controller_services must be a non-empty list")

    if errors:
        print("architecture-check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "architecture-check: PASS "
        f"({len(required_paths)} paths, {len(declared_set)} backend capabilities)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
