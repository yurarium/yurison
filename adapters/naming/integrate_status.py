#!/usr/bin/env python3
"""Write the job's one-shot verdicts into `data/completion-reviewed.yaml`, each checked as a person's.

The other half of `status_items.py`. Each answer for a work the job was asked about becomes an
entry in the register's own shape and has to pass `completion.problems`, the test a hand-written
verdict passes, before it is written at the end of `works:`. A work the register already holds is
never overwritten, and an answer that fails is reported with its reason and not written.

    integrate_status.py --answers result.json --items data/build/status-items.json
"""
import argparse
import datetime
import json
import pathlib
import sys
import urllib.parse

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import completion                                                       # noqa: E402
import textnorm                                                         # noqa: E402
from integrate import answers_of                                        # noqa: E402

#: What the job may answer. `completed` and `continuing` are a person's: the job is asked whether a
#: work is a one-shot, and its answer to that is one of these.
ANSWERS = ("oneshot", completion.SERIALISED, "unsettled")


def plain(s):
    return " ".join(str(s or "").replace("—", ", ").split())


def entry(answer, today):
    """The register's entry for one answer."""
    e = {"verdict": answer.get("verdict"), "basis": plain(answer.get("basis"))}
    if answer.get("verdict") != "unsettled":
        if plain(answer.get("basis_en")):
            e["basis_en"] = plain(answer.get("basis_en"))
        e["source_kind"] = answer.get("source_kind")
        url = (answer.get("source_url") or "").strip()
        if url:
            e["source"] = urllib.parse.urlparse(url).netloc or None
            e["source_url"] = url
    e["reviewed"] = today
    return {k: v for k, v in e.items() if v}


def render(key, e):
    L = [f"  {json.dumps(key, ensure_ascii=False)}:"]
    for k in ("verdict", "basis", "basis_en", "source", "source_kind", "source_url"):
        if e.get(k):
            L.append(f"    {k}: {json.dumps(e[k], ensure_ascii=False)}")
    L.append(f"    reviewed: '{e['reviewed']}'")
    return "\n".join(L) + "\n"


def drop(text, key):
    """`text` without the entry for `key` under `works:`: its head line and every line indented
    deeper than it, up to the next entry."""
    heads = {f"  {key}:", f"  {json.dumps(key, ensure_ascii=False)}:", f"  '{key}':"}
    out, skipping = [], False
    for line in text.split("\n"):
        if line in heads:
            skipping = True
            continue
        if skipping and (line.startswith("    ") or not line.strip()):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out)


def integrate(text, answers, asked, today):
    """`(new text, written keys, [(key, reason)])`."""
    # AN `unsettled` ENTRY IS ASKED AGAIN after `status_items.AGAIN` days, and its answer replaces it.
    works = (yaml.safe_load(text) or {}).get("works") or {}
    held = {textnorm.norm(w) for w, e in works.items() if (e or {}).get("verdict") != "unsettled"}
    stale = {textnorm.norm(w): w for w, e in works.items() if (e or {}).get("verdict") == "unsettled"}
    blocks, written, refused, seen = [], [], [], set()
    for a in answers:
        key = a.get("key")
        if key not in asked:
            refused.append((key, "not a work it was asked about"))
            continue
        if textnorm.norm(key) in held or key in seen:
            refused.append((key, "already reviewed"))
            continue
        if a.get("verdict") not in ANSWERS:
            refused.append((key, f"verdict {a.get('verdict')!r} is not one of {ANSWERS}"))
            continue
        e = entry(a, today)
        bad = completion.problems(key, e)
        if bad:
            refused.append((key, "; ".join(bad)))
            continue
        seen.add(key)
        if textnorm.norm(key) in stale:
            text = drop(text, stale[textnorm.norm(key)])
        blocks.append(render(key, e))
        written.append((key, e["verdict"]))
    for key in sorted(set(asked) - {a.get("key") for a in answers}):
        refused.append((key, "no answer"))
    if not blocks:
        return text, written, refused
    return text.rstrip("\n") + "\n" + "".join(blocks), written, refused


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--answers", required=True)
    ap.add_argument("--items", default="data/build/status-items.json")
    ap.add_argument("--register", default=str(completion.FILE))
    a = ap.parse_args(argv)

    result = json.loads(pathlib.Path(a.answers).read_text(encoding="utf-8") or "{}")
    asked = {i["key"] for i in json.loads(pathlib.Path(a.items).read_text(encoding="utf-8"))}
    path = pathlib.Path(a.register)
    text, written, refused = integrate(path.read_text(encoding="utf-8"),
                                       answers_of(result, "verdicts"), asked,
                                       datetime.date.today().isoformat())
    if written:
        path.write_text(text, encoding="utf-8")
    print(f"{len(written)} verdict(s) written, {len(refused)} not")
    for key, v in written:
        print(f"  {v:10} {key}")
    for key, why in refused:
        print(f"  {key}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
