import os
from pathlib import Path

EXCLUDE_DIRS = {".venv", "venv", "env", "__pycache__", ".git"}

def should_exclude(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)

def process_file(p: Path) -> int:
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return 0

    lines = text.splitlines(True)
    removed = 0
    out = []

    for ln in lines:
        s = ln.lstrip()
        if s.startswith("#") and not s.startswith("#!") and "coding" not in s[:20]:
            removed += 1
            continue
        out.append(ln)

    if removed > 0:
        p.write_text("".join(out), encoding="utf-8")
    return removed

def main() -> None:
    base = Path(".")
    py_files = [p for p in base.rglob("*.py") if not should_exclude(p)]
    total_removed = 0
    for p in py_files:
        total_removed += process_file(p)
    print(f"Processed {len(py_files)} files; removed {total_removed} full-line comment(s).")

if __name__ == "__main__":
    main()