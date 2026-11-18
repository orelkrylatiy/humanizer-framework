#!/usr/bin/env python3
"""Проверка навыка и манифестов без сторонних зависимостей."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
header = re.match(r"\A---\n(.*?)\n---\n", skill, re.DOTALL)
assert header, "Отсутствуют метаданные навыка"
version = re.search(r'(?m)^\s+version:\s*"([0-9]+\.[0-9]+\.[0-9]+)"', header.group(1))
assert version, "Отсутствует metadata.version"
assert "name: humanizer" in header.group(1)
assert "license: MIT" in header.group(1)
assert "## " + version.group(1) in changelog
patterns = re.findall(r"(?m)^### (\d+)\. (.+)$", skill)
assert len(patterns) == 26
assert [int(n) for n, _ in patterns] == list(range(1, 27))
table = re.findall(r"(?m)^\| (\d+) \| (.+?) \|$", readme)
assert table == patterns, "README и SKILL.md расходятся"
assert len(skill.split()) <= 5500
claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
cursor = json.loads((ROOT / ".cursor-plugin/plugin.json").read_text())
market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
pi = json.loads((ROOT / "package.json").read_text())
assert claude["version"] == cursor["version"] == version.group(1)
assert claude["skills"] == ["./"]
assert "skills" not in cursor
assert market["plugins"][0]["source"] == "./"
assert pi["pi"]["skills"] == ["./"]
assert list(ROOT.rglob("SKILL.md")) == [ROOT / "SKILL.md"]
print("Humanizer skill v" + version.group(1) + ": 26 правил, манифесты проверены")
