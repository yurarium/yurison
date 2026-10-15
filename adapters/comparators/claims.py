#!/usr/bin/env python3
"""Turn comparator listings into PROVISIONAL update claims (REQUIREMENTS §5).

A deliberate relaxation, decided 2026-08-01. Web漫画アンテナ and 百合ナビ are Tier C and remain
non-attesting for bibliographic fields, but for the narrow question *"did this work update, and
roughly when"* their listings are now taken as **provisionally true** and shown in the feed.

The reasoning: those two sites are the acceptance criterion. Holding the feed to platform-attested
releases only meant the feed was structurally incapable of meeting the criterion for platforms we
cannot reach — and a reader looking for "what updated" is better served by a claim marked as a
claim than by silence.

What this does NOT change:

- These claims establish **no `marketing_label`, no `content_tier`, and no bibliographic field**.
  A bare listing is still not corroboration (REQUIREMENTS §1).
- Every claim carries `provenance: claimed` and names the site. Platform-attested releases carry
  `provenance: attested`. The two are never merged into an undifferentiated "release", and the
  interface must keep them distinguishable.
- Where a platform attests the same work on the same date, the attested record wins and the claim
  is dropped — a claim is a floor, not an addition.

Usage:  claims.py --out data/source/comparators --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys
import unicodedata
from collections import Counter
from datetime import date

import yaml

sys.path.insert(0, "adapters/webcomics")
from coverage import parse  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import paths

MIN_CLAIMS = 20


def norm(s):
    s = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", s or "")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"""[\s\-.=、。･・!?,:;'"“”‘’()\[\]{}「」『』【】〈〉《》〔〕~〜_/\\|+*&#@]""",
                  "", s.strip().lower())


def month_day(month, day, taken):
    """A date printed without a year, read as the latest such day on or before `taken`.

    A listing never shows a future update, so 12月30日 on a page fetched in January is last year.
    """
    for y in (taken.year, taken.year - 1):
        try:
            d = date(y, month, day)
        except ValueError:
            continue
        if d <= taken:
            return d
    return None


def antenna_date(txt, taken):
    """The day a listing row says its work updated, read against the day the page was fetched.

    `taken` is the fetch, not the run: a page the fetch could not refresh still says 3時間前 of
    the day it was taken, and dating that to the run would invent an update.
    """
    t = (txt or "").strip()
    if "分前" in t or "時間前" in t:
        return taken
    m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", t)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})月(\d{1,2})日", t)
    if m:
        return month_day(int(m.group(1)), int(m.group(2)), taken)
    return None


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--days", type=int, default=60, help="how far back to emit claims")
    a = ap.parse_args()

    today = date(*(int(x) for x in a.retrieved.split("-")))
    cutoff = date.fromordinal(today.toordinal() - a.days)

    claims, seen = [], set()

    # ── Web漫画アンテナ ────────────────────────────────────────────────
    cache = paths.cache("webcomics-cache")
    rows = []
    for f in sorted(cache.glob("page*.html"),
                    key=lambda p: int(re.search(r"\d+", p.name).group())):
        taken = min(today, date.fromtimestamp(f.stat().st_mtime))
        rows += [(r, taken) for r in parse(f.read_text())]
    for r, taken in rows:
        d = antenna_date(r["updated_text"], taken)
        if not d or not (cutoff <= d <= today):
            continue
        k = (norm(r["title"]), str(d))
        if k in seen:
            continue
        seen.add(k)
        claims.append({"work": r["title"], "platform": r["platform"], "date": str(d),
                       "url": r["work_url"], "source": "webcomics.jp",
                       "tags": r.get("tags") or []})

    # ── 百合ナビ WEB連載 ──────────────────────────────────────────────
    yf = pathlib.Path("data/coverage/yurinavi-webyuri.yaml")
    if yf.exists():
        doc = yaml.safe_load(yf.read_text()) or {}
        taken = min(today, date.fromisoformat(str(doc.get("retrieved") or today)))
        for w in doc.get("works") or []:
            lu = str(w.get("last_update_seen") or "")
            m = re.match(r"(\d{2})-(\d{2})", lu)
            if not m:
                continue
            d = month_day(int(m.group(1)), int(m.group(2)), taken)
            if not d:
                continue
            if not (cutoff <= d <= today):
                continue
            # 百合ナビ runs title and author together; keep the raw cell rather than guess a split.
            k = (norm(w["raw"]), str(d))
            if k in seen:
                continue
            seen.add(k)
            claims.append({"work": w["raw"], "platform": w["platform"], "date": str(d),
                           "url": None, "source": "yurinavi", "raw_cell": True})

    if len(claims) < MIN_CLAIMS:
        sys.exit(f"HEALTH: {len(claims)} claims (< {MIN_CLAIMS}). Refusing to write.")

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = ["# PROVISIONAL UPDATE CLAIMS from the comparator sites.",
         "#",
         "# Taken as provisionally true for ONE question only: that a work updated, and roughly",
         "# when. They establish no marketing_label, no content_tier and no bibliographic field —",
         "# a bare listing is still not corroboration (REQUIREMENTS §1).",
         "#",
         "# Every entry carries provenance: claimed. Platform-attested releases carry",
         "# provenance: attested, and the two are never merged.",
         "source: comparators", "role: provisional-claims", f"retrieved: {a.retrieved}",
         "record_type: update_claims", f"window_days: {a.days}",
         f"claims: {len(claims)}", "updates:"]
    for c in sorted(claims, key=lambda c: (c["date"], c["work"]), reverse=True):
        L.append(f"  - work: {js(c['work'])}")
        L.append(f"    platform: {js(c['platform'])}")
        L.append(f"    date: {c['date']}")
        L.append(f"    source: {js(c['source'])}")
        L.append("    provenance: claimed")
        if c.get("url"):
            L.append(f"    url: {js(c['url'])}")
        if c.get("raw_cell"):
            L.append("    raw_cell: true   # title and author unsplit")
        if c.get("tags"):
            L.append(f"    listing_tags: {js(c['tags'])}")
    L.append("")
    (out / "claims.yaml").write_text("\n".join(L))

    by_src = Counter(c["source"] for c in claims)
    print(f"claims written : {len(claims)}  {dict(by_src)}")
    print(f"window         : {cutoff} → {today}")
    print(f"written        : {out}/claims.yaml")


if __name__ == "__main__":
    main()
