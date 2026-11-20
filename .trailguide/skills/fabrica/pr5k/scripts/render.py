#!/usr/bin/env python3
"""Render a PR5K snapshot (JSON) into one self-contained HTML page.

Usage: render.py SNAPSHOT.json OUT.html
"""
import datetime
import html
import json
import pathlib
import sys

REQUIRED = ["schemaVersion", "pr"]
SECTIONS = ["overview", "database", "backend", "frontend", "architecture", "principles", "verification", "media"]


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    snap_path, out_path = map(pathlib.Path, sys.argv[1:])
    data = json.loads(snap_path.read_text())
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        print(f"snapshot is missing {', '.join(missing)}", file=sys.stderr)
        return 1
    if not any(k in data for k in SECTIONS):
        print("snapshot has no sections", file=sys.stderr)
        return 1
    template = (pathlib.Path(__file__).resolve().parent.parent / "assets" / "canvas.html").read_text()
    # A rescan the page asked for ends when it loads a page rendered after the request.
    data["renderedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    pr = data["pr"]
    title = f"{pr['repo'].split('/')[-1].capitalize()} PR {pr['number']}"
    # Keep the embedded JSON from closing its script element early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = template.replace("__PR_TITLE__", html.escape(title)).replace("__PR_DATA__", payload)
    out_path.write_text(page)
    print(f"wrote {out_path} ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
