"""Move a finished work order out of the live folders into Archive/ (never deletes).

  .venv/Scripts/python forge/archive.py <project> [--note "what was built"]

Workbench/<project>  ->  Archive/<YYYY-MM-DD>_<project>/workbench
Assets/<project>     ->  Archive/<YYYY-MM-DD>_<project>/assets   (only if still present)
WorkOrders/<project>.md is copied alongside, and a line is appended to Archive/LOG.md.
"""
import datetime
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    project = sys.argv[1]
    note = sys.argv[sys.argv.index("--note") + 1] if "--note" in sys.argv else ""
    stamp = datetime.date.today().isoformat()
    dest = ROOT / "Archive" / f"{stamp}_{project}"
    n = 2
    while dest.exists():
        dest = ROOT / "Archive" / f"{stamp}_{project}_{n}"
        n += 1
    moved = []
    for src, name in ((ROOT / "Workbench" / project, "workbench"), (ROOT / "Assets" / project, "assets")):
        if src.exists():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest / name))
            moved.append(name)
    order = ROOT / "WorkOrders" / f"{project}.md"
    if order.exists():
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(order, dest / order.name)
        moved.append("work order")
    if not moved:
        sys.exit(f"nothing found for project {project!r}")
    log = ROOT / "Archive" / "LOG.md"
    if not log.exists():
        log.write_text("# Archive log\n\n")
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"- {stamp} **{project}** -> `{dest.name}/` ({', '.join(moved)}){' - ' + note if note else ''}\n")
    print(f"archived {', '.join(moved)} -> {dest}")


if __name__ == "__main__":
    main()
