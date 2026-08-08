#!/usr/bin/env python3
"""key.py: one definition of the name-store key, and what it must not fold together."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import key  # noqa: E402

COVERS = ["adapters/names/key.py"]


def main(s):
    # THE PAIR THE FOLD EXISTS FOR, quoted from the corpus: one work arriving from two platforms.
    s.eq(key.fold("彼氏の女友達がぐいぐい来る（私に）"), key.fold("彼氏の女友達がぐいぐい来る(私に)"),
         "full-width and half-width brackets are one key")
    s.eq(key.fold("Ａ　Ｂ"), key.fold("A B"), "and so are width and the two spaces")
    s.eq(key.fold("A B"), "AB", "the space is gone rather than narrowed")
    s.eq(key.fold(None), "", "no name is the empty key, not a crash")

    # WHAT IT MUST NOT FOLD. MADB drops the ！ from its subtitle field and keeps it in the reading,
    # so 勝たん and 勝たん！ arrive as two strings. Joining them is a decision somebody takes, and a
    # fold that did it here would also join titles that genuinely differ by their punctuation.
    s.ne(key.fold("ギャルメイドと悪役令嬢 : おじょーさまのハッピーエンドしか勝たん"),
         key.fold("ギャルメイドと悪役令嬢 : おじょーさまのハッピーエンドしか勝たん！"),
         "an exclamation mark is part of a title")
    # And a bracketed edition marker stays, because this is a name key and not a work identity.
    # `identity.fold` strips those on purpose; one rendering must not serve two titles a reader can
    # tell apart.
    s.ne(key.fold("リバティ"), key.fold("リバティ【合本版】"),
         "a name key keeps what identity deliberately removes")

    # THE COPY IN THE BROWSER. This is the string check.py holds the interface to, so the test says
    # what it is: a change here has to be made in both places or the shipped map stops answering.
    s.eq(key.fold("彩純ちゃん　1"), "彩純ちゃん1",
         "NFKC folds the ideographic space to an ordinary one, so stripping ASCII covers both")

    # A KEY THAT APPLIES ONLY BECAUSE SPACES WERE STRIPPED is still worth reporting to whoever typed
    # it, which is why the distinction survived the merge of the two folds.
    s.check(key.spaced("彩純ちゃん 1", "彩純ちゃん1"), "a stray space is a key that applies by accident")
    s.check(not key.spaced("彩純ちゃん（1）", "彩純ちゃん(1)"),
            "a width difference is one spelling of one work and is not reported")
    s.check(not key.spaced("あ", "い"), "and two different names are not a spacing question")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
