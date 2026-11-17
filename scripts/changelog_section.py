"""Print one version's section of CHANGELOG.md (used for release notes).

Usage:  python scripts/changelog_section.py 0.4.0
Exits non-zero if the version has no section, so a release can't go out
without describing what changed.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def section(version: str, text: str) -> str | None:
    """Return the body under "## [version]" up to the next "## " heading."""
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else None


if __name__ == "__main__":
    version = sys.argv[1]
    body = section(version, CHANGELOG.read_text(encoding="utf-8"))
    if not body:
        sys.exit(f"CHANGELOG.md has no section for [{version}]")
    print(body)
