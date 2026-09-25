#!/usr/bin/env python3
"""Validate projects.json: every project has a detail page and every asset path exists.

Run before pushing:  python check.py
Missing assets are warnings (placeholders are fine); missing pages are errors.
"""
import json, pathlib, sys

root = pathlib.Path(__file__).parent
data = json.loads((root / "data" / "projects.json").read_text(encoding="utf-8"))

errors, warnings = [], []

for p in data["projects"]:
    slug = p["slug"]
    for field in ("title", "summary", "hero"):
        if not p.get(field):
            errors.append(f"{slug}: missing required field '{field}'")

    page = root / "projects" / f"{slug}.html"
    if not page.exists():
        errors.append(f"{slug}: no detail page at projects/{slug}.html")

    paths = [p["hero"], *(g["src"] for g in p.get("gallery", []))]
    if p.get("model"):
        paths.append(p["model"])
    for rel in paths:
        if not (root / rel).exists():
            warnings.append(f"{slug}: asset not found: {rel}")

for w in warnings:
    print(f"warn: {w}")
for e in errors:
    print(f"ERROR: {e}")

print(f"\n{len(data['projects'])} projects, {len(errors)} errors, {len(warnings)} missing assets")
sys.exit(1 if errors else 0)
