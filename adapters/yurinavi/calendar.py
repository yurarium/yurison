#!/usr/bin/env python3
"""百合ナビ 発売日カレンダー — captured, deliberately NOT wired to anything.

A volume-release schedule (単行本 and digital), by date, with the 出版元 covering both publishers
and platforms. A different axis from the web-chapter feed in §5: this is the catalogue side.

**Status: captured only.** Output goes to `data/unwired/` and is read by nothing — not the build,
not the site. The interesting part is forthcoming releases, which no bibliographic source carries
yet, and that turns out to be of uncertain value. Rather than lose the parsing while it is
understood, it is written down and left disconnected.

To wire it up later: the shape below is stable, and `data/unwired/` is outside the source tree, so
the build's allowlist will not admit it by accident.

Two things any future consumer must respect:

- Tier C, discovery only (REQUIREMENTS §1). 百合ナビ is not a source of truth, and a listed date
  attests nothing. Confirm against openBD or MADB before it becomes a field.
- **A scheduled date is a claim about the future, not an observation.** Release dates slip. Under
  §5 a date is fixed at first sight from evidence held at that point; a forthcoming date is not
  evidence of anything having happened, and must never be stored as a publication date.

Usage:  calendar.py --out data/unwired --cache $YURI_CACHE/yurinavi-cache \
                    --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.request
from collections import Counter

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
URL = "https://yurinavi.com/yuri-calendar/"
MIN_ROWS = 20


def fetch(cache, force=False):
    f = cache / "calendar.html"
    if f.exists() and not force:
        return f.read_text()
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(1.2)
    f.write_text(t)
    return t


def text(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()


def parse(html):
    """Rows are `<d/m weekday> | | <title (vol) author> | <publisher>`, under ▼<n>月発売 headers.

    The volume number sits in parentheses before the author, and title and author run together in
    one cell. Splitting them reliably needs the publisher's own record, so the cell is kept whole
    (REQUIREMENTS §6: quarantine rather than guess).
    """
    out, month, day = [], None, None
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if not cells:
            continue
        m = re.search(r"▼\s*(\d{1,2})\s*月発売", " ".join(cells))
        if m:
            month, day = int(m.group(1)), None
            continue
        d = re.match(r"^(\d{1,2})/(\d{1,2})", cells[0]) if cells[0] else None
        if d:
            month, day = int(d.group(1)), int(d.group(2))
        body = [c for c in cells[1:] if len(c) > 2]
        if len(body) < 2 or month is None or day is None:
            continue
        raw, publisher = body[0], body[-1]
        vol = re.search(r"[（(](\d+)[）)]", raw)
        out.append({
            "raw": raw,
            "volume": int(vol.group(1)) if vol else None,
            "publisher": publisher,
            "date": f"{month:02d}-{day:02d}",
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    rows = parse(fetch(cache, a.force))
    if len(rows) < MIN_ROWS:
        sys.exit(f"HEALTH: parsed {len(rows)} rows (< {MIN_ROWS}). Refusing to write.")

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = ["# 百合ナビ 発売日カレンダー — CAPTURED, NOT WIRED.",
         "#",
         "# Read by nothing: not the build, not the site. Kept so the parsing is not lost.",
         "#",
         "# Tier C, discovery only. 百合ナビ is not a source of truth (REQUIREMENTS §1), and a date",
         "# here attests nothing. A SCHEDULED date is a claim about the future — release dates slip",
         "# — so it must never be stored as a publication date (§5).",
         "#",
         "# `raw` holds title, volume number and author together; splitting them needs the",
         "# publisher's own record.",
         "source: yurinavi-calendar", "role: discovery-only", "status: captured-not-wired",
         f"retrieved: {a.retrieved}", "record_type: release_calendar",
         f"entries: {len(rows)}", "releases:"]
    for r in rows:
        L.append(f"  - raw: {json.dumps(r['raw'], ensure_ascii=False)}")
        L.append(f"    scheduled: {r['date']}")
        if r["volume"] is not None:
            L.append(f"    volume: {r['volume']}")
        L.append(f"    publisher: {json.dumps(r['publisher'], ensure_ascii=False)}")
    L.append("")
    (out / "yurinavi-calendar.yaml").write_text("\n".join(L))

    months = Counter(r["date"][:2] for r in rows)
    print(f"entries captured : {len(rows)}")
    print(f"months           : {dict(sorted(months.items()))}")
    print(f"distinct 出版元   : {len({r['publisher'] for r in rows})}")
    print(f"written          : {out}/yurinavi-calendar.yaml  (wired to nothing)")


if __name__ == "__main__":
    main()
