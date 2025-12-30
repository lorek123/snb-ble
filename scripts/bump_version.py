#!/usr/bin/env python3
"""Simple script to bump version in pyproject.toml and __init__.py."""

import re
import sys
from pathlib import Path

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"
INIT_PY = PROJECT_ROOT / "src" / "storzandbickel_ble" / "__init__.py"


def get_current_version() -> str:
    """Extract current version from pyproject.toml."""
    content = PYPROJECT_TOML.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def bump_version(current: str, part: str) -> str:
    """Bump version by the specified part (major, minor, patch)."""
    parts = current.split(".")
    if len(parts) != 3:
        # Handle pre-release versions (e.g., "0.1.0a1")
        base_version = re.match(r"(\d+)\.(\d+)\.(\d+)", current)
        if not base_version:
            raise ValueError(f"Invalid version format: {current}")
        parts = list(base_version.groups())
        suffix = current[len(".".join(parts)) :]
    else:
        suffix = ""

    major, minor, patch = map(int, parts)

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid part: {part}. Must be 'major', 'minor', or 'patch'")

    return f"{major}.{minor}.{patch}{suffix}"


def update_file(file_path: Path, old_version: str, new_version: str) -> None:
    """Update version in a file."""
    content = file_path.read_text()
    # Replace version in pyproject.toml format
    content = re.sub(
        rf'version = "{re.escape(old_version)}"',
        f'version = "{new_version}"',
        content,
    )
    # Replace version in __init__.py format
    content = re.sub(
        rf'__version__ = "{re.escape(old_version)}"',
        f'__version__ = "{new_version}"',
        content,
    )
    file_path.write_text(content)
    print(f"✓ Updated {file_path.relative_to(PROJECT_ROOT)}")


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py <major|minor|patch>")
        print("\nExamples:")
        print("  python scripts/bump_version.py patch  # 0.1.0 → 0.1.1")
        print("  python scripts/bump_version.py minor  # 0.1.0 → 0.2.0")
        print("  python scripts/bump_version.py major  # 0.1.0 → 1.0.0")
        sys.exit(1)

    part = sys.argv[1].lower()
    if part not in ("major", "minor", "patch"):
        print(f"Error: Invalid part '{part}'. Must be 'major', 'minor', or 'patch'")
        sys.exit(1)

    try:
        current_version = get_current_version()
        new_version = bump_version(current_version, part)

        print(f"Bumping version: {current_version} → {new_version}")

        update_file(PYPROJECT_TOML, current_version, new_version)
        update_file(INIT_PY, current_version, new_version)

        print(f"\n✓ Version bumped successfully to {new_version}")
        print("\nNext steps:")
        print("  1. Review changes: git diff")
        print(f"  2. Commit: git commit -am 'Bump version to {new_version}'")
        print(f"  3. Tag: git tag v{new_version}")
        print(f"  4. Push: git push origin main && git push origin v{new_version}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
