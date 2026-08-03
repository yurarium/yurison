#!/usr/bin/env python3
"""What curate.py must refuse, and what must survive being applied twice."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import curate  # noqa: E402
from names.store import NameStore  # noqa: E402

COVERS = ["adapters/names/curate.py"]

LICENSED = {"en": "Otherside Picnic", "basis": "licensed", "source": "Square Enix Manga & Books",
            "source_kind": "licensor", "source_url": "https://example.invalid/otherside",
            "reviewed": "2026-08-03"}
OURS = {"en": "Wine Girls", "basis": "translated", "source": "yurarium",
        "source_kind": "derived", "reviewed": "2026-08-03"}


def with_(**kw):
    e = dict(LICENSED)
    e.update(kw)
    return {k: v for k, v in e.items() if v is not None}


def main(s):
    s.eq(curate.problems("titles", "x", LICENSED), [], "a licensed title with a licensor page")
    s.eq(curate.problems("titles", "x", OURS), [], "our own translation, no source page owed")

    # The project owner's rule, now enforced rather than remembered.
    s.check(curate.problems("titles", "x", with_(source_kind="community-db",
                                                 source="Wikipedia",
                                                 source_url="https://example.invalid/w")),
            "a community database may not supply an attributed name")
    s.check(curate.problems("titles", "x", with_(basis="official-jp")),
            "a licensor page cannot establish the work's OWN English name")
    s.check(curate.problems("titles", "x", with_(source_url=None)),
            "an attributed name needs the page it was read from")
    s.check(curate.problems("titles", "x", with_(basis="translated", source_kind="derived",
                                                 source_url=None, en="Otherside Picnic")) == [],
            "a translation needs no page, because it is not a finding")
    s.check(curate.problems("titles", "x", with_(reviewed=None)),
            "an entry with no review date")
    s.check(curate.problems("titles", "x", with_(bais="licensed")),
            "a misspelt key is an error rather than a silent no-op")
    s.check(curate.problems("titles", "x", with_(candidate="Otherside Picnic")),
            "an entry cannot be both attributed and a candidate")
    s.check(curate.problems("titles", "x", {"candidate": "Stardust Telepath",
                                            "source": "Wikipedia",
                                            "source_kind": "community-db",
                                            "reviewed": "2026-08-03"}) == [],
            "a community database is a fine source for a CANDIDATE")
    s.check(curate.problems("titles", "x", {"candidate": "Stardust Telepath", "basis": "licensed",
                                            "source": "Wikipedia", "source_kind": "community-db",
                                            "reviewed": "2026-08-03"}),
            "a candidate carrying a basis is a claim in disguise")
    s.check(curate.check({"titels": {}}), "an unknown top-level key")

    with tempfile.TemporaryDirectory() as d:
        doc = {"titles": {"裏世界ピクニック": LICENSED, "ワインガールズ": OURS,
                          "星屑テレパス": {"candidate": "Stardust Telepath", "source": "Wikipedia",
                                      "source_kind": "community-db", "reviewed": "2026-08-03"}}}
        st = NameStore(d)
        # A romanised string already in place, which is what the passes leave behind.
        st.record("titles", "ワインガールズ", en="Wain Gāruzu", basis="romaji", source="derived")
        applied, cands = curate.apply(st, doc)
        s.eq((applied, cands), (2, 1), "two attributed, one candidate")
        rec = st.records["titles"]
        s.eq(rec["裏世界ピクニック"]["en"], "Otherside Picnic", "the licensed title lands")
        s.eq(rec["ワインガールズ"]["en"], "Wine Girls", "a translation outranks a romanisation")
        s.check("Wain Gāruzu" in str(rec["ワインガールズ"].get("en_conflicts")),
                "the displaced romanisation is kept rather than discarded")
        s.check(not rec["星屑テレパス"].get("en"), "a candidate never becomes the name")
        s.eq(rec["星屑テレパス"]["en_candidates"][0]["value"], "Stardust Telepath",
             "the candidate is recorded where a later fetch can settle it")
        s.eq(rec["裏世界ピクニック"]["en_at"], "2026-08-03",
             "the stamp is the review date, not the day this ran")

        curate.apply(st, doc)
        s.eq(len(rec["星屑テレパス"]["en_candidates"]), 1, "re-applying the file changes nothing")
        s.eq(rec["ワインガールズ"]["en"], "Wine Girls", "and does not disturb an applied name")
        st.close()

    # The shipped file must itself pass, or the check is a thing that only tests fixtures.
    s.eq(curate.check(curate.load()), [], "the file in the repository validates")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
