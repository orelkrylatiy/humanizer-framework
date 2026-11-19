#!/usr/bin/env python3
"""Validate Markdown Mermaid blocks; render all diagrams when mmdc is installed.

Usage:
    python scripts/check_mermaid.py docs README.md
    python scripts/check_mermaid.py --require-render --puppeteer-config /tmp/puppeteer.json docs

Static checks need only the Python standard library. CI installs mmdc.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OPEN = re.compile(r"^\s*```mermaid\s*$", re.MULTILINE)
BLOCK = re.compile(r"^\s*```mermaid\s*\n(.*?)^\s*```\s*$", re.MULTILINE | re.DOTALL)
NUMBERED_LINK_STYLE = re.compile(r"\blinkStyle\s+\d+\b")
TYPES = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "gantt",
    "journey",
    "pie",
    "mindmap",
    "timeline",
    "quadrantChart",
    "gitGraph",
    "sankey-beta",
)


def markdown_files(roots: list[Path]):
    seen: set[Path] = set()
    for root in roots:
        candidates = root.rglob("*.md") if root.is_dir() else [root]
        for path in candidates:
            if path.suffix != ".md" or any(part.startswith(".") for part in path.parts):
                continue
            path = path.resolve()
            if path not in seen:
                seen.add(path)
                yield path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*", type=Path, default=[Path("docs"), Path("README.md")]
    )
    parser.add_argument(
        "--require-render",
        action="store_true",
        help="fail if mmdc is missing; render all diagrams to SVG",
    )
    parser.add_argument(
        "--puppeteer-config",
        type=Path,
        help="optional mmdc -p config JSON, e.g. --no-sandbox in CI",
    )
    args = parser.parse_args()

    diagrams: list[tuple[Path, int, str]] = []
    errors: list[str] = []
    for path in markdown_files(args.paths):
        source = path.read_text(encoding="utf-8")
        matches = list(BLOCK.finditer(source))
        opened = list(OPEN.finditer(source))
        if len(opened) != len(matches):
            errors.append(f"{path}: {len(opened)} Mermaid fences open, {len(matches)} closed")
        for n, match in enumerate(matches, 1):
            diagram = match.group(1).strip()
            if not diagram.startswith(TYPES):
                errors.append(f"{path}: diagram {n} has no recognized Mermaid type")
            if NUMBERED_LINK_STYLE.search(diagram):
                errors.append(f"{path}: diagram {n} uses fragile numeric linkStyle")
            diagrams.append((path, n, diagram))

    if errors:
        for err in errors:
            print("ERROR:", err, file=sys.stderr)
        return 1

    cli = shutil.which("mmdc")
    if args.require_render and not cli:
        print(
            "ERROR: --require-render needs @mermaid-js/mermaid-cli (mmdc)",
            file=sys.stderr,
        )
        return 1

    if cli:
        with tempfile.TemporaryDirectory(prefix="mermaid-check-") as temp:
            for index, (path, num, diagram) in enumerate(diagrams):
                src = Path(temp) / f"{index:03d}.mmd"
                dst = src.with_suffix(".svg")
                src.write_text(diagram + "\n", encoding="utf-8")
                cmd = [cli, "-i", str(src), "-o", str(dst)]
                if args.puppeteer_config:
                    cmd.extend(["-p", str(args.puppeteer_config.resolve())])
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if result.returncode or not dst.is_file() or b"<svg" not in dst.read_bytes()[:2048]:
                    print(f"ERROR: Mermaid render failed: {path} diagram {num}", file=sys.stderr)
                    print((result.stderr or result.stdout)[-5000:], file=sys.stderr)
                    return 1
        print(f"OK: {len(diagrams)} Mermaid diagrams rendered to SVG.")
    else:
        print(
            f"OK: {len(diagrams)} Mermaid diagrams passed static checks; "
            "mmdc not installed, rendering not verified."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
