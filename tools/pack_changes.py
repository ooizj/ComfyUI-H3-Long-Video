"""Pack uncommitted changes into a zip for another machine.

    python tools/pack_changes.py [--base HEAD] [--notes dist/NOTES.md]

Writes dist/<repo>-changes_<base>_<time>.zip with files/ (added or modified files), DELETED.txt
and CHANGES.md (the notes plus the base commit and file list).
"""

import argparse
from datetime import datetime
import os
import subprocess
import zipfile


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True, text=True).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--notes", default="dist/NOTES.md")
    args = parser.parse_args()
    root = git(".", "rev-parse", "--show-toplevel").strip()
    base = git(root, "rev-parse", args.base).strip()

    changed, deleted = [], []
    fields = git(root, "diff", "--name-status", "--no-renames", "-z", base).split("\0")
    for status, path in zip(fields[0::2], fields[1::2]):
        (deleted if status.startswith("D") else changed).append(path)
    changed += [p for p in git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0") if p]

    notes_path = os.path.join(root, args.notes)
    notes = open(notes_path, encoding="utf-8").read().strip() + "\n\n" if os.path.isfile(notes_path) else ""
    changes = (f"{notes}Base commit: {base}\n\nFiles:\n" + "".join(f"- {p}\n" for p in sorted(changed))
               + ("\nDelete:\n" + "".join(f"- {p}\n" for p in deleted) if deleted else ""))

    output = os.path.join(root, "dist", f"{os.path.basename(root)}-changes_{base[:7]}_"
                                        f"{datetime.now():%Y%m%d_%H%M%S}.zip")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in changed:
            bundle.write(os.path.join(root, path), "files/" + path)
        bundle.writestr("DELETED.txt", "".join(p + "\n" for p in deleted))
        bundle.writestr("CHANGES.md", changes)
    print(f"{output}\n{len(changed)} file(s), {len(deleted)} deletion(s)")


if __name__ == "__main__":
    main()
