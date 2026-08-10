#!/usr/bin/env python3
"""worklist: the queue for choosing an English name, and what each row's job actually is.

COVERS = ['adapters/names/worklist.py']

THE FAULT A QUEUE COMMITS is sending somebody to work that does not exist. The first run of this
module put 30 titles under `compose` whose own name is already in Latin letters, so a reviewer
working it in order would have started by translating `GIRL FRIENDS` into English.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import worklist                                                         # noqa: E402


def _build(d, titles, series):
    at = pathlib.Path(d)
    (at / "feed").mkdir(parents=True, exist_ok=True)
    (at / "feed" / "names.json").write_text(json.dumps({"titles": titles}, ensure_ascii=False))
    (at / "series.json").write_text(json.dumps({"series": series}, ensure_ascii=False))
    return str(at)


def main(s):
    with tempfile.TemporaryDirectory() as d:
        titles = {
            # A base with a real English name, and the same work under edition apparatus.
            "冬木先輩と夏井": {"en": "Fuyuki-senpai and Natsui", "basis": "translated"},
            "【完結】冬木先輩と夏井": {"basis": "romaji",
                              "romaji": {"macron": "[Kanketsu] Fuyuki Senpai to Natsui"}},
            # A base whose own English is a romanisation, so joining changes a spelling only.
            "球詠": {"en": "Tamayomi", "basis": "romaji", "romaji": {"macron": "Tamayomi"}},
            "球詠【単話版】": {"basis": "romaji", "romaji": {"macron": "Tamayomi (Tanwaban)"}},
            # Already the work's own Latin name.
            "GIRL FRIENDS": {"basis": "romaji", "romaji": {"macron": "GIRL FRIENDS"}},
            "schadenliebe": {"basis": "romaji", "romaji": {"macron": "schadenliebe"}},
            # Latin names carrying marks an approved-punctuation list did not hold.
            'She "Falls" in Love': {"basis": "romaji"},
            "YuRe：Log": {"basis": "romaji"},
            "maimaimaimai mind！": {"basis": "romaji"},
            "Rouge　caprice": {"basis": "romaji"},
            # A short kana coinage.
            "ナキノン": {"basis": "romaji", "romaji": {"macron": "Nakinon"}},
            # A phrase nobody has named.
            "犬も歩けば姫に当たる": {"basis": "romaji",
                            "romaji": {"macron": "Inu mo Arukeba Hime ni Ataru"}},
            "さろめりっく": {"basis": "romaji", "romaji": {"macron": "Saro Meri Kku"}},
            "レンズのむこう": {"basis": "romaji", "romaji": {"macron": "Renzu no Mukō"}},
            "イヴとイヴ": {"basis": "romaji", "romaji": {"macron": "Ivu to Ivu"}},
            # And one that is already settled, which must not appear at all.
            "やがて君になる": {"en": "Bloom Into You", "basis": "licensed"},
        }
        series = [{"id": f"w{i:05}", "work": k} for i, k in enumerate(titles)]
        build = _build(d, titles, series)
        got = {r["work"]: r["route"] for r in worklist.rows(build)}

        s.check("やがて君になる" not in got, "a work with a licensed name is not in the queue")
        s.eq(got.get("【完結】冬木先輩と夏井"), "inherit",
             "a variant whose base has a real English name is inherit and needs no decision")
        s.eq(got.get("球詠【単話版】"), "inherit-romaji",
             "a variant whose base carries a romanisation is consistency work and says so")

        # THE ONE THE FIRST RUN GOT WRONG. A title already in Latin letters is the work's own name.
        s.eq(got.get("GIRL FRIENDS"), "already-latin", "a Latin title needs no English rendering")
        s.eq(got.get("schadenliebe"), "already-latin", "including a lowercase one")

        # WHAT MAKES IT LATIN IS THE ABSENCE OF JAPANESE. A list of approved punctuation held none
        # of these four and sent every one of them to somebody to translate into English.
        for latin in ('She "Falls" in Love', "YuRe：Log", "maimaimaimai mind！", "Rouge　caprice"):
            s.eq(got.get(latin), "already-latin", f"{latin} is already its own name, marks and all")
        s.check(not worklist.already_latin("球詠"), "and a title with no Latin letters is not")
        s.check(not worklist.already_latin("Fate/kaleid ライナー"),
                "nor is one mixing the two, which still owes a rendering of its Japanese")
        s.ne(got.get("GIRL FRIENDS"), "compose",
             "and it is not sent to somebody to translate, which is what it was")

        s.eq(got.get("ナキノン"), "coinage", "a short kana title is a coinage to confirm")
        s.eq(got.get("さろめりっく"), "broken-romanisation",
             "kana written straight through, romanised with spaces nobody wrote, is a reading fault")
        # A PARTICLE IS A STATED DIVISION even with no space around it, and the first version of
        # that rule called both of these broken. They are right.
        s.eq(got.get("レンズのむこう"), "compose", "a kana phrase divides at its particle")
        s.eq(got.get("イヴとイヴ"), "compose", "and so does a pair joined by と")
        s.eq(got.get("犬も歩けば姫に当たる"), "compose", "a phrase nobody has named needs one written")

        # EVERY ROUTE IS DOCUMENTED, or the queue tells a reviewer what to do in a name alone.
        named = {r for r, _why in worklist.ROUTES}
        s.eq(set(got.values()) - named, set(), "every route a row can take is described in ROUTES")
        s.check(all(why.strip() for _r, why in worklist.ROUTES), "and each description says something")

    # THE ROUTES ARE ORDERED BY WHAT COSTS LEAST TO SETTLE, which is the point of the module:
    # inheriting needs no decision, composing needs research, and the last two need neither.
    s.eq([r for r, _ in worklist.ROUTES][:2], ["inherit", "compose"],
         "the queue leads with the rows that can be settled and then the ones that need looking")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "worklist"))
