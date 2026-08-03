#!/usr/bin/env python3
"""resolve.py: the pass runner and its progress report.

COVERS = ['adapters/names/resolve.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import resolve


def main(s):
    # The passes are addressable by name, so a run can be bounded to one of them.
    s.check(hasattr(resolve, "run_pass"), "a single pass can be run on its own")
    s.check(hasattr(resolve, "report"), "progress can be reported without running anything")

    # HERE anchors the sibling passes, and it must be the module's own directory rather than the
    # working directory, or running resolve.py from anywhere else silently finds no passes.
    s.eq(resolve.HERE, pathlib.Path(resolve.__file__).resolve().parent,
         "the pass directory is anchored to this module, not to the caller's cwd")
    s.check((resolve.HERE / "pass1_kana.py").exists(),
            "and the passes really are beside it, so the anchor is not merely plausible")

    # Every pass named by the runner must exist, or a run bounded to it fails at the far end of a
    # long job rather than at the start.
    for n in (0, 1, 2, 3, 4):
        hits = list(resolve.HERE.glob(f"pass{n}_*.py"))
        s.check(hits, f"pass {n} exists on disk")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.resolve"))
