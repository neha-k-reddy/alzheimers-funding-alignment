"""
clean_notebooks.py
==================
Clears saved cell outputs from all Jupyter notebooks in analysis/notebooks/.

Notebook outputs (rendered tables, charts, error messages) are runtime artifacts
from when the notebook was last executed. They're useful when you have the
original data on disk, but for public repos, they:

  - Add file size (ours have ~470KB of saved outputs each)
  - Show stale errors when files referenced in the notebook aren't available
    (e.g., raw CDC data folders that exist on Colab but not in the repo)
  - Get out of sync with the code they purport to demonstrate

Standard practice: clear outputs before committing notebooks to public repos.
The code is preserved exactly; only saved outputs are stripped.

Usage (from project root):
    python3 analysis/clean_notebooks.py
"""

import json
import sys
from pathlib import Path

NOTEBOOK_DIR = Path(__file__).parent / "notebooks"


def clear_notebook(path: Path) -> bool:
    """Clear outputs and execution counts from one notebook. Returns True if changed."""
    with open(path, "r") as f:
        nb = json.load(f)

    changed = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs"):
            cell["outputs"] = []
            changed = True
        if cell.get("execution_count") is not None:
            cell["execution_count"] = None
            changed = True

    if changed:
        with open(path, "w") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
            f.write("\n")
    return changed


def main():
    if not NOTEBOOK_DIR.exists():
        print(f"ERROR: {NOTEBOOK_DIR} does not exist.")
        sys.exit(1)

    notebooks = sorted(NOTEBOOK_DIR.glob("*.ipynb"))
    if not notebooks:
        print(f"No notebooks found in {NOTEBOOK_DIR}.")
        sys.exit(1)

    print(f"Found {len(notebooks)} notebook(s):\n")
    for nb_path in notebooks:
        size_before = nb_path.stat().st_size
        changed = clear_notebook(nb_path)
        size_after = nb_path.stat().st_size

        kb_before = size_before / 1024
        kb_after = size_after / 1024
        if changed:
            print(f"  ✓ {nb_path.name}: {kb_before:.1f} KB → {kb_after:.1f} KB (cleared)")
        else:
            print(f"  · {nb_path.name}: {kb_after:.1f} KB (already clean)")

    print("\nDone. Code preserved, outputs cleared.")


if __name__ == "__main__":
    main()
