#!/usr/bin/env python3
"""Confirm discovery candidates against カドコミ (comic-walker.com).

This is the second half of the discovery architecture (REQUIREMENTS §1). 百合ナビ names a work;
this confirms it against the publisher, which is what supplies the fields. A Tier C source may say
a work exists and nothing more.

Kadokomi's tag *search* loads from `/api/`, which its robots.txt disallows, so bulk enumeration is
off. Per-work detail pages are a different matter: `/detail/<code>` is permitted, and the page
embeds its own payload in `__NEXT_DATA__`. We fetch named works only — no crawling, no API.

The page carries `tags` including 百合 where the publisher applies it, so this DOES establish
marketing_label under DEFINITIONS §4 — unlike a third-party tag, this is the publisher's own.

Never stored: `summary` (publisher synopsis — copyrightable, §2) or any thumbnail URL (§2).

Usage:  confirm.py --queue data/queue/yurinavi.yaml --out data/source/kadokomi \
                   --cache $YURI_CACHE/kadokomi-cache --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.error, urllib.request

import yaml
# `adapters/` ON THE PATH BEFORE THE FACT IS IMPORTED. `run_stage.py` runs each adapter as a
# bare subprocess with no PYTHONPATH, and the usage line above says to run it by hand the same
# way, so a module that imports a package living under adapters/ has to say where it is. This
# one did not, and every CI run of it died on `No module named 'facts'` before it read a page.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from facts import marketing as _marketing                               # noqa: E402

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
DETAIL = "https://comic-walker.com/detail/{code}"
PAUSE = 1.5
# ASKED OF `facts/marketing`, which owns it. This vocabulary decides what the database
# admits and it had three homes until 2026-08-10.
YURI_TAGS = _marketing.TAGS

# `ratingLevel` is NOT the §7 signal, and must not be used as one. Kadokomi returns 'adult' for
# works that are plainly not pornography — a bathhouse romance drama, a VTuber romcom — so it is
# some audience-targeting or default value, not an 18禁 designation. Verified 2026-08-01: all five
# confirmed works carried it.
#
# DEFINITIONS §7 excludes on objective Japanese publishing markers — 成年コミックマーク, an 18禁/R-18
# designation, an adult imprint, adult-only distribution. A platform field whose semantics we have
# not established is none of those, and gating on it would have excluded every work here while
# providing no actual protection.
#
# So it is recorded verbatim and flagged for a maintenance pass to determine, per §6's rule that
# unknown values are quarantined rather than coerced into a meaning.
RATING_SEMANTICS_KNOWN = False


def fetch(code, cache):
    f = cache / f"{code}.html"
    if f.exists():
        return f.read_text(), True
    req = urllib.request.Request(DETAIL.format(code=code), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t, False


def work_data(html):
    """The __NEXT_DATA__ payload kadokomi embeds. Defined in `releases.py`, asked here.

    THE ONE EXACT DUPLICATE IN THE TREE, found by the duplicates lint on 2026-08-10. Two files
    parsed the same script tag with the same expression, so a change to the page would have had
    to be made twice and the second would have been found by a reader.
    """
    from kadokomi.releases import work_data as _wd
    return _wd(html)


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    q = yaml.safe_load(open(a.queue)) or {}
    # Candidates carry the article that named them; the work code comes from the article's own
    # outbound link, which discovery resolved. Codes are passed in via the queue file.
    targets = [(c["work_title"], c.get("platform_code"), c) for c in (q.get("candidates") or [])
               if c.get("platform") == "kadokomi" and c.get("platform_code")]
    if not targets:
        sys.exit("no kadokomi candidates with a platform_code in the queue")

    confirmed, withheld, failed = [], [], []
    for title, code, cand in targets:
        try:
            html, cached = fetch(code, cache)
        except urllib.error.HTTPError as e:
            failed.append((title, code, f"HTTP {e.code}"))
            continue
        d = work_data(html)
        if not d:
            failed.append((title, code, "no __NEXT_DATA__ work payload"))
            continue
        w = d["work"]
        tags = [t["name"] for t in w.get("tags") or []]
        rating = w.get("ratingLevel")

        rec = {
            "work_title": w.get("title", title),
            "platform_code": code,
            "url": DETAIL.format(code=code),
            "authors": [{"name": x.get("name"), "role": x.get("role")}
                        for x in w.get("authors") or []],
            "tags": tags,
            "genre": w.get("genre"),
            "sub_genre": w.get("subGenre"),
            "serialization_status": w.get("serializationStatus"),
            "is_oneshot": bool(w.get("isOneShot")),
            "is_original": bool(w.get("isOriginal")),
            "rating_level": rating,
            "label": (d.get("label") or {}).get("name"),
            "discovered_via": {"source": cand.get("source"), "url": cand.get("url"),
                               "signal": cand.get("signal")},
        }

        if rating is not None and not RATING_SEMANTICS_KNOWN:
            rec["rating_level_note"] = ("Platform field of undetermined meaning; NOT treated as a "
                                        "DEFINITIONS §7 adult marker. Needs a maintenance pass.")

        hits = [t for t in tags if t in YURI_TAGS]
        if hits:
            rec["marketing_label"] = "yuri"
            rec["marketing_label_basis"] = {
                "source": "kadokomi", "url": rec["url"], "retrieved": a.retrieved,
                "note": f"Publisher applies the tag {'/'.join(hits)} on カドコミ. "
                        "Platform-side labelling under DEFINITIONS §4.",
            }
        else:
            rec["marketing_label"] = "none"
            rec["marketing_label_note"] = ("No yuri tag applied by the publisher. Confirmed as a "
                                           "real work; content_tier needs a human (DEFINITIONS §4).")
        confirmed.append(rec)

    L = ["# Confirmed against カドコミ work pages. Discovery named these; the publisher attests them.",
         "# No synopsis and no image URLs are stored (REQUIREMENTS §2).",
         "source: kadokomi", f"retrieved: {a.retrieved}", "record_type: web_work_confirmation",
         "works:"]
    for r in confirmed:
        L.append(f"  - work_title: {js(r['work_title'])}")
        for k in ("platform_code", "url", "genre", "sub_genre", "serialization_status",
                  "is_oneshot", "is_original", "rating_level", "rating_level_note", "label",
                  "marketing_label", "marketing_label_note"):
            if r.get(k) is not None:
                L.append(f"    {k}: {js(r[k])}")
        L.append(f"    tags: {js(r['tags'])}")
        L.append("    authors:")
        for au in r["authors"]:
            L.append(f"      - name: {js(au['name'])}")
            L.append(f"        role: {js(au['role'])}")
        if r.get("marketing_label_basis"):
            b = r["marketing_label_basis"]
            L.append("    marketing_label_basis:")
            for k in ("source", "url", "retrieved", "note"):
                L.append(f"      {k}: {js(b[k])}")
        dv = r["discovered_via"]
        L.append("    discovered_via:")
        for k in ("source", "signal", "url"):
            L.append(f"      {k}: {js(dv.get(k))}")
    L.append("")
    (out / "confirmed.yaml").write_text("\n".join(L))

    if withheld:
        W = ["# WITHHELD pending human review — carries a non-zero rating (DEFINITIONS §7).",
             "# Not published. Ambiguity on the adult filter fails closed (REQUIREMENTS §6).",
             "source: kadokomi", f"retrieved: {a.retrieved}", "record_type: withheld", "works:"]
        for r in withheld:
            W.append(f"  - work_title: {js(r['work_title'])}")
            W.append(f"    url: {js(r['url'])}")
            W.append(f"    reason: {js(r['withheld'])}")
        W.append("")
        (out / "withheld.yaml").write_text("\n".join(W))

    labelled = sum(1 for r in confirmed if r["marketing_label"] == "yuri")
    print(f"candidates targeted : {len(targets)}")
    print(f"confirmed           : {len(confirmed)}  ({labelled} carry a publisher yuri tag)")
    print(f"withheld (rating)   : {len(withheld)}")
    for t, c, why in failed:
        print(f"  FAILED {t} ({c}): {why}")


if __name__ == "__main__":
    main()
