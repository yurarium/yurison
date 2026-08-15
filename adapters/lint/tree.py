#!/usr/bin/env python3
"""Which files are this repository's own, asked of git and not of the filesystem.

WHY THIS IS A MODULE. `budget_stock_phrasing_in_comments` learned this alone and wrote it in its
own docstring: walking the directory counted a file git ignores, so the same commit measured 903 in
the main tree and 898 in a worktree, a branch ratcheted the budget down in good faith, and the merge
put it straight back. A number that depends on which tree you stand in cannot ratchet.

WHAT MADE IT A CLASS. Agent worktrees live at `.claude/worktrees/agent-*`, INSIDE the repository.
Two of them turned `invented markup in tests` from 75 into 225 and `three as an organising shape`
from 27 into 81, both exactly three times their real value, because every walker counted every file
once per tree. `facts with more than one home` went from 12 to 1,737, since a file copied into three
trees really does look like a fact with three homes. Each of those numbers is a budget that only
ratchets down, so a green run in that state would have written a floor nothing could ever meet again.

Git already answers this correctly and answers it the same way from any tree: a nested worktree is a
different working tree with its own index, and `git ls-files` never reports another one's contents.
So the fix is to stop walking.
"""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]


def own_files(*suffixes, root=None, under=None):
    """Every file in this working tree that git would show, tracked or newly written.

    `suffixes` filters by extension (".py", ".md"); `under` restricts to a subdirectory. Both are
    conveniences, and the point of the function is the enumeration.

    A FILE WRITTEN AN HOUR AGO IS AS MUCH THIS TREE'S AS ONE COMMITTED LAST YEAR, and leaving the
    first kind out cost a CI run. This asked for
    tracked files alone, so a module written and not yet committed was invisible to every lint
    built on it: `./check.py --gate` answered `all right` on a tree holding a new suite that opened
    its own database, and the same gate failed on the runner, where the file was committed and
    therefore visible. The rule a person runs the gate to be told about is the rule about the work
    they have just done.

    `--exclude-standard` KEEPS THE NESTED-WORKTREE ARGUMENT INTACT, which is what this module is
    for: `.claude/worktrees/` is ignored, so an agent's copy of the repository stays out of the
    count, and so does everything else .gitignore names.

    FALLS BACK TO WALKING where git cannot answer, because a check that reads nothing reports zero
    and a zero is indistinguishable from clean. The fallback skips nested worktrees by name, which
    is the case that made this module, and it is the weaker answer of the two.
    """
    at = pathlib.Path(root or ROOT)
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others",
                              "--exclude-standard"], cwd=str(at),
                             capture_output=True, text=True, timeout=60)
        names = [n for n in out.stdout.split("\0") if n] if out.returncode == 0 else []
    except Exception:                                                   # noqa: BLE001
        names = []
    # THE NESTED-TREE RULE IS APPLIED TO BOTH ANSWERS NOW. `git ls-files` never reports another
    # working tree's INDEX, which is what this module was written on; `--others` reports files, and
    # an agent's worktree is a directory of files. `.claude/` is in .gitignore, so today the flag
    # excludes them anyway, and a guarantee that rests on a line somebody could delete is not one.
    if names:
        paths = [at / n for n in names if not _inside_another_tree(at / n, at)]
    else:
        paths = [p for p in at.rglob("*")
                 if p.is_file() and not _inside_another_tree(p, at)]
    if under:
        want = at / under
        paths = [p for p in paths if want in p.parents]
    if suffixes:
        paths = [p for p in paths if p.suffix in suffixes]
    return sorted(p for p in paths if p.exists())


#: Directories that hold a checkout of this same repository. A file under one of these is another
#: tree's copy of a file this tree already has.
NESTED_TREES = (".claude/worktrees", ".git")


def _inside_another_tree(path, root):
    rel = str(path.relative_to(root))
    return any(rel.startswith(d + "/") or f"/{d}/" in f"/{rel}" for d in NESTED_TREES)


if __name__ == "__main__":
    got = own_files(".py")
    print(f"{len(got)} tracked .py file(s) in {ROOT}")
