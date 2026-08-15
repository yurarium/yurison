#!/usr/bin/env python3
"""lint/tree: which files are this repository's own, asked of git.

COVERS = ['adapters/lint/tree.py']

THE FAULT THIS IS FOR is a count that depends on which tree you stand in. Two agent worktrees at
`.claude/worktrees/` read `invented markup in tests` as 225 where it is 75 and `three as an
organising shape` as 81 where it is 27, both exactly three times, because every walker counted every
file once per checkout. Those are budgets that only ratchet down, so a green run in that state
writes a floor no later run can meet.
"""
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import tree                                                             # noqa: E402


def _repo(at, files, ignored=()):
    """A real git repository, because what is being tested is what git answers."""
    at = pathlib.Path(at)
    subprocess.run(["git", "init", "-q", str(at)], check=True, capture_output=True)
    for name, body in files.items():
        p = at / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    if ignored:
        (at / ".gitignore").write_text("\n".join(ignored) + "\n")
    subprocess.run(["git", "add", "-A"], cwd=str(at), check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "x"], cwd=str(at), check=True, capture_output=True)
    return at


def main(s):
    with tempfile.TemporaryDirectory() as d:
        at = _repo(d, {"a.py": "x = 1\n", "docs/b.md": "# b\n", "sub/c.py": "y = 2\n"})

        got = {p.name for p in tree.own_files(root=at)}
        s.check({"a.py", "b.md", "c.py"} <= got, "every tracked file is reported")
        s.eq({p.name for p in tree.own_files(".py", root=at)}, {"a.py", "c.py"},
             "and a suffix filter reports only those")
        s.eq({p.name for p in tree.own_files(".py", root=at, under="sub")}, {"c.py"},
             "and `under` restricts to a subdirectory")

        # THE CASE THIS MODULE EXISTS FOR. A checkout of the repository INSIDE the repository is
        # another tree's copy of files this tree already has, and git never reports it.
        nested = at / ".claude" / "worktrees" / "agent-x"
        nested.mkdir(parents=True)
        (nested / "a.py").write_text("x = 1\n")
        (nested / "sub").mkdir()
        (nested / "sub" / "c.py").write_text("y = 2\n")
        after = tree.own_files(".py", root=at)
        s.eq(len(after), 2, "a nested checkout does not double the count, ignored or not")
        s.check(not any(".claude" in p.parts for p in after),
                "and nothing under it is reported at all")

        # A FILE GIT IGNORES IS NOT THIS REPOSITORY'S, which is the fault the stock-phrasing budget
        # met first: the same commit measured 903 in one tree and 898 in another. `.claude/` above
        # is one, and so is anything else .gitignore names.
        (at / ".gitignore").write_text("scratch.py\n")
        (at / "scratch.py").write_text("z = 3\n")
        s.check(not any(p.name == "scratch.py" for p in tree.own_files(".py", root=at)),
                "a file git ignores is not counted as the repository's own")

        # A FILE NOT COMMITTED YET IS STILL IN THE TREE, and this asked for tracked files alone
        # until a CI run paid for it: a new suite that opened its own database was invisible to
        # every lint built on this, `./check.py --gate` answered `all right`, and the same commit
        # failed on the runner where the file was tracked. The gate is run to be told about the
        # work somebody has just done.
        (at / "written.py").write_text("z = 4\n")
        s.check(any(p.name == "written.py" for p in tree.own_files(".py", root=at)),
                "a file written and not yet committed is the repository's own")

    # WHERE GIT CANNOT ANSWER, IT STILL ANSWERS SOMETHING. A check that reads nothing reports zero,
    # and a zero is indistinguishable from clean, so the fallback walks and skips nested trees.
    with tempfile.TemporaryDirectory() as d:
        at = pathlib.Path(d)
        (at / "a.py").write_text("x = 1\n")
        (at / ".claude" / "worktrees" / "agent-y").mkdir(parents=True)
        (at / ".claude" / "worktrees" / "agent-y" / "a.py").write_text("x = 1\n")
        got = tree.own_files(".py", root=at)
        s.eq(len(got), 1, "with no git at all, the walk still skips a nested worktree")
        s.check(got and got[0].name == "a.py", "and reports the file that is really here")

    # AND IT ANSWERS FOR THIS REPOSITORY, which is what every caller passes no root for.
    mine = tree.own_files(".py")
    s.check(len(mine) > 100, "this repository's own Python files are found")
    s.check(not any(".claude" in p.parts for p in mine),
            "and no worktree of it is among them, whatever is on disk today")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "tree"))
