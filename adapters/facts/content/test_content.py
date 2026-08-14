#!/usr/bin/env python3
"""facts/content: the register of what a source flagged, read once.

COVERS = ['adapters/facts/content/__init__.py']

WHAT CAN BE WRONG HERE IS THAT A FLAG GOES UNREAD, which is the fault the register exists to end.
Five works sat flagged `not published` for the life of the project while all five were live, because
nothing consumed the file.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import content                                              # noqa: E402


def _tree():
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "kadokomi").mkdir()
    (d / "kadokomi" / "withheld.yaml").write_text(
        "source: kadokomi\nworks:\n"
        "  - work_title: 'あ'\n    reason: 'adult'\n    withhold: true\n"
        "  - work_title: 'い'\n    reason: 'adult'\n", encoding="utf-8")
    (d / "editions").mkdir()
    (d / "editions" / "withheld.yaml").write_text(
        "works:\n  - work_title: 'う'\n    reason: 'imprint'\n", encoding="utf-8")
    (d / "editions" / "other.yaml").write_text("works:\n  - work_title: 'え'\n", encoding="utf-8")
    return d


def main(s):
    got = content.flags(_tree())
    s.eq(sorted(got), ["あ", "い", "う"], "every register under the tree is read")
    s.check("え" not in got, "and a file that is not a register is not one")

    # A FLAG WITHHOLDS ONLY WHERE IT SAYS SO, which is the reviewed decision and is the whole
    # difference between recording a flag and acting on it.
    s.eq(got["あ"]["withhold"], True, "a flag saying withhold withholds")
    s.eq(got["い"]["withhold"], False, "and one that says nothing does not")

    # THE SOURCE IS THE FILE'S OWN FIELD WHERE IT HAS ONE, and its directory otherwise, so a
    # register that never named itself is still attributable.
    s.eq(got["あ"]["source"], "kadokomi", "a register naming its source is believed")
    s.eq(got["う"]["source"], "editions", "and one that does not is named for where it sits")

    # `key` IS THE CALLER'S, because two callers fold differently on purpose: the build keys on a
    # work-title fold so a flag matches whatever spelling a platform used, and the store keys on
    # the title as written. A default here would make one of them silently wrong.
    folded = content.flags(_tree(), key=lambda t: t + "!")
    s.eq(sorted(folded), ["あ!", "い!", "う!"], "the caller's fold decides the key")
    s.eq(folded["あ!"]["title"], "あ", "and the title travels unfolded beside it")

    s.eq(content.flags(pathlib.Path(tempfile.mkdtemp())), {},
         "a tree with no register answers nothing rather than raising")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
