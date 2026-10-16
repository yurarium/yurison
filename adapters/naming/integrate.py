#!/usr/bin/env python3
"""Write the naming job's answers into `data/names/curated.yaml`, each checked as a person's would be.

The job answers in JSON against `adapters/naming/schema.json` and never sees this repository. This is
the other half: each answer for a title it was asked about becomes an entry in the house format,
passes `curate.problems`, the same test a hand-written entry passes, and is written at the end of
the `titles:` section. An answer that fails is not written, and its reason is printed for the run's
record; an answer the job declined (`skip`) is reported as declined.

WHAT IT REFUSES BEYOND curate: a key it was not asked about, a key the file already holds, a basis
whose source kind does not fit it, an attributed name with no page, and a note too thin to say why.

    integrate.py --answers result.json --items data/build/naming-items.json
"""
import argparse
import datetime
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from names import curate                                                # noqa: E402

#: The bases the job may answer on, each with the source kinds curate lets stand behind it.
#: `stated` is left out: it is a reading of the record, never a finding of research.
FITS = {b: curate.ATTRIBUTION[b] for b in ("official-jp", "licensed", "translated", "romaji")}
NOTE_MIN = 40


def entry(answer, today):
    """`(entry, None)` in the curated file's shape, or `(None, reason)`."""
    if answer.get("skip"):
        return None, f"declined: {answer['skip']}"
    basis, kind = answer.get("basis"), answer.get("source_kind")
    if basis not in FITS:
        return None, f"basis {basis!r} is not one of {sorted(FITS)}"
    if kind not in FITS[basis]:
        return None, f"a {basis} name cannot rest on a {kind!r} source"
    en = (answer.get("en") or "").strip()
    note = " ".join((answer.get("note") or "").replace("—", ", ").split())
    if not en:
        return None, "no English name"
    if len(note) < NOTE_MIN:
        return None, "the note does not say why"
    e = {"en": en, "basis": basis}
    if kind == "derived":
        e.update(source=curate.OURS, source_kind="derived")
    else:
        url = (answer.get("source_url") or "").strip()
        if not url.startswith("http"):
            return None, f"a {basis} name has to cite the page that states it"
        e.update(source=(answer.get("source") or url.split("/")[2]), source_kind=kind,
                 source_url=url)
        # A SECOND FORM IS KEPT ONLY WHEN IT IS ONE. Our rendering beside the publisher's name has
        # to differ in its words and say what it rests on, as curate requires; one that does not is
        # dropped and the attributed name stands alone, which costs nothing the record had.
        tr = (answer.get("translation") or "").strip()
        tn = " ".join((answer.get("translation_note") or "").replace("\u2014", ", ").split())
        if tr and tn and not curate._same_words(tr, en):
            e.update(translation=tr, translation_note=tn)
    e["reviewed"] = today
    e["note"] = note
    return e, None


def render(key, e):
    """One entry as the file writes entries."""
    L = [f"  {json.dumps(key, ensure_ascii=False)}:"]
    for k in ("en", "translation", "basis", "source", "source_kind", "source_url"):
        if e.get(k):
            L.append(f"    {k}: {json.dumps(e[k], ensure_ascii=False)}")
    L.append(f"    reviewed: '{e['reviewed']}'")
    for k in ("note", "translation_note"):
        if e.get(k):
            L.append(f"    {k}: >-")
            L.append(f"      {e[k]}")
    return "\n".join(L) + "\n"


def insert(text, blocks):
    """`text` with `blocks` at the end of its `titles:` section."""
    at = text.find("\nauthors:\n")
    if at < 0:
        raise SystemExit("curated.yaml has no authors: section to write before")
    return text[:at + 1] + "".join(blocks) + text[at + 1:]


def answers_of(result):
    """The `names` list from the folded result: its structured output, or JSON in its text."""
    got = result.get("structured_output")
    if not got:
        text = result.get("result") or ""
        start = text.find("{")
        try:
            got = json.loads(text[start:]) if start >= 0 else {}
        except ValueError:
            got = {}
    return (got or {}).get("names") or []


def integrate(text, answers, asked, today):
    """`(new text, written keys, [(key, reason)])` for one run's answers."""
    held = set(((yaml.safe_load(text) or {}).get("titles") or {}))
    blocks, written, refused, seen = [], [], [], set()
    for a in answers:
        key = a.get("key")
        if key not in asked:
            refused.append((key, "not a title it was asked about"))
            continue
        if key in held or key in seen:
            refused.append((key, "already named"))
            continue
        e, why = entry(a, today)
        if why:
            refused.append((key, why))
            continue
        bad = curate.problems("titles", key, e)
        if bad:
            refused.append((key, "; ".join(bad)))
            continue
        seen.add(key)
        blocks.append(render(key, e))
        written.append(key)
    for key in sorted(set(asked) - {a.get("key") for a in answers}):
        refused.append((key, "no answer"))
    return (insert(text, blocks) if blocks else text), written, refused


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--answers", required=True)
    ap.add_argument("--items", default="data/build/naming-items.json")
    ap.add_argument("--curated", default=str(curate.FILE))
    a = ap.parse_args(argv)

    result = json.loads(pathlib.Path(a.answers).read_text(encoding="utf-8") or "{}")
    asked = {i["key"] for i in json.loads(pathlib.Path(a.items).read_text(encoding="utf-8"))}
    path = pathlib.Path(a.curated)
    text, written, refused = integrate(path.read_text(encoding="utf-8"), answers_of(result), asked,
                                       datetime.date.today().isoformat())
    if written:
        path.write_text(text, encoding="utf-8")
    print(f"{len(written)} name(s) written, {len(refused)} not")
    for key, why in refused:
        print(f"  {key}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
