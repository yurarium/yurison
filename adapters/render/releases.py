#!/usr/bin/env python3
"""Chapter lists from client-rendered platforms (REQUIREMENTS §5, §6).

Twenty-five hosts hold their chapter list in JavaScript and serve HTML that contains none of it.
No amount of fetching reaches them, and that had been recorded as a standing decision to make —
"add a browser to the pipeline" — weighed against pixivコミック alone and declined.

It is cheaper than that assessment assumed. Chromium renders a page to DOM from the command line
with `--headless --dump-dom`; there is no Python dependency to add, no driver, no service. マガポケ
returns 33 KB of shell to a fetch and 757 KB of rendered DOM with twenty dated episodes.

This is not the thing refused for pixivコミック's API. That refusal was about claiming to be a
browser in order to pass an access control. Here we ARE a browser, running the page as written and
reading what it chose to display, and still saying who we are in the user agent.

Cost is real and is why this is a separate adapter rather than a fallback inside another: several
seconds and a browser process per page, against milliseconds for a fetch. Renders are cached, and
a platform reachable any other way must not be listed here.

Dates carry `date_basis: rendered` — read from a page the platform drew, which is weaker than a
feed it published and stronger than a pattern matched in markup.

Usage:  releases.py --targets data/coverage/render-targets.yaml --out data/source/webpages \
                    --cache ~/workspace/render-cache --retrieved 2026-08-01
"""
import argparse, html as _html, json, pathlib, re, subprocess, sys, time
from collections import Counter

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "recon"))
from extract import (CHAPTERISH, norm_date, try_jsonld, try_markup,  # noqa: E402
                     try_next, try_pairs)

CHROME = None
for c in ("/snap/bin/chromium", "/usr/bin/chromium", "/usr/bin/chromium-browser",
          "/usr/bin/google-chrome"):
    if pathlib.Path(c).exists():
        CHROME = c
        break

UA = "Mozilla/5.0 (compatible; yurarium/0.1; +https://yurarium.github.io/)"
BUDGET_MS = 8000
PAUSE = 1.0
MIN_EPISODES = 2


def render(url, cache, max_age_days=2):
    key = re.sub(r"[^A-Za-z0-9]", "_", url)[-120:]
    f = cache / f"{key}.html"
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
        return f.read_text()
    if not CHROME:
        sys.exit("no chromium found; this adapter needs a browser binary on the system")
    out = subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
         f"--virtual-time-budget={BUDGET_MS}", f"--user-agent={UA}", "--dump-dom", url],
        capture_output=True, text=True, timeout=120)
    time.sleep(PAUSE)
    html = out.stdout or ""
    if len(html) < 2000:
        return ""
    f.write_text(html)
    return html


# Platforms whose rendered chapter list has a stable structure worth reading directly. The generic
# strategies find a date and a label and nothing else; these carry access per chapter, which is the
# field the free view depends on and which no heuristic can recover.
STRUCTURED = {
    # マガポケ: <li class="c-episode-items__item"> … __date, __ttl, and an icon that is either
    # __ico--free or __ico--point with a price on it.
    "magapoke": {
        "item": r'<li class="c-episode-items__item">',
        "date": r'__date">([^<]*)<',
        "title": r'__ttl">([^<]*)<',
        "access": r'__ico--(\w+)">([^<]*)<',
    },
    # マンガワン names nothing semantically — the classes are utility soup — but the item container
    # is stable and the badges are plain text: 無料 for free, 先読 for a chapter released early to
    # paying readers (which is why some carry a future date).
    "mangaone": {
        "item": r'<div class="cursor-pointer block border-b-1',
        "date": r'<p class="text-xs text-gray-700[^"]*">(\d{4}/\d{1,2}/\d{1,2})</p>',
        "title": r'<p class="line-clamp-1[^"]*">([^<]*)</p>',
        "free_marker": r'>無料<',
        "advance_marker": r'先読|先行',
    },
}


def episodes_structured(html, spec):
    out = []
    for b in re.split(spec["item"], html)[1:]:
        d = re.search(spec["date"], b)
        ti = re.search(spec["title"], b)
        if not (d and ti):
            continue
        date = norm_date(d.group(1))
        title = re.sub(r"\s+", " ", _html.unescape(ti.group(1))).strip()
        if not date or not title:
            continue
        row = {"title": title, "updated": date}
        if spec.get("free_marker"):
            # Presence-based rather than a captured value: the badge either appears or it does not.
            row["access_modes"] = ["free"] if re.search(spec["free_marker"], b) else ["purchase"]
            if spec.get("advance_marker") and re.search(spec["advance_marker"], b):
                row["access_note"] = "released early to paying readers (先読)"
        ico = re.search(spec["access"], b) if spec.get("access") else None
        if ico:
            kind = ico.group(1)
            row["access_modes"] = ["free"] if kind == "free" else ["purchase"]
            if kind != "free" and ico.group(2).strip():
                row["price"] = ico.group(2).strip()
        out.append(row)
    return out


def episodes(html):
    """The rendered DOM is still just markup, so the proven strategies apply unchanged."""
    got = try_jsonld(html) or try_next(html)
    if len(got) < MIN_EPISODES:
        got, _ = try_markup(html)
    if len(got) < MIN_EPISODES:
        # Nested chapter lists, where title and date are not in a common repeated container.
        got = try_pairs(html)
    out, seen = [], set()
    for g in got:
        title = re.sub(r"\s+", " ", g.get("title") or "").strip()
        date = g.get("date")
        if not date or not CHAPTERISH.search(title):
            continue
        # A rendered DOM carries interface text the markup never had — "移動", view counters,
        # like counts — and it lands either side of the chapter label: "移動 【第1話】甘すぎる恋",
        # "16 【最終回(2)】聖夜の天使たち 55 55". Start at a bracket if the label opens with one,
        # otherwise at the chapter marker itself, and cut at the first trailing run of digits.
        m = CHAPTERISH.search(title)
        start = m.start()
        br = title.rfind("【", 0, m.start())
        if br >= 0 and m.start() - br < 12:
            start = br
        label = title[start: m.end() + 40]
        label = re.split(r"\s\d{4}[-/.年]\d{1,2}|\s+\d{2,}(?:\s|$)", label)[0]
        label = label.strip(" 　·・|/-")
        if (label, date) in seen:
            continue
        seen.add((label, date))
        out.append({"title": label, "updated": date})
    return out


# Interface words that can follow a title and are not an author.
_NOT_AUTHOR = re.compile(r"^(UP|NEW|更新|無料|お気に入り|シェア|クリップ|[0-9]|次回|最新話|全話|第|話数|続きを読む)")


def author_near_title(html, title):
    """The author sits directly under the work title, as text rather than in an attribute.

    マガポケ renders it that way — 「オカルトタイムズ」 then 「いどんち」 on the next line — and every
    pattern that looked for an author-ish class or JSON key found nothing, because there is none.
    Positional, so it is validated: a short line that is not interface furniture, else nothing.
    """
    if not title:
        return None
    body = html[html.find("<body"):]
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S)
    lines = [l.strip() for l in re.sub(r"<[^>]+>", "\n", body).split("\n") if l.strip()]
    for i, line in enumerate(lines):
        if title in line and len(line) <= len(title) + 4:
            for nxt in lines[i + 1: i + 3]:
                if 1 <= len(nxt) <= 24 and not _NOT_AUTHOR.match(nxt):
                    return nxt
            return None
    return None


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit-per-host", type=int, default=40)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    spec = yaml.safe_load(open(a.targets)) or {}
    for plat in spec.get("platforms") or []:
        rows, failed = [], Counter()
        for t in (plat.get("works") or [])[: a.limit_per_host]:
            try:
                html = render(t["url"], cache)
            except subprocess.TimeoutExpired:
                failed["timeout"] += 1
                continue
            if not html:
                failed["empty render"] += 1
                continue
            spec = STRUCTURED.get(plat["id"])
            eps = episodes_structured(html, spec) if spec else []
            if len(eps) < MIN_EPISODES:
                eps = episodes(html)
            if len(eps) >= MIN_EPISODES:
                row = {"work_title": t.get("title"), "url": t["url"], "episodes": eps}
                au = author_near_title(html, t.get("title"))
                if au:
                    row["author"] = au
                rows.append(row)
            else:
                failed["no dated chapters"] += 1

        if not rows:
            print(f"{plat['name'][:20]:22} nothing parsed  {dict(failed)}")
            continue
        L = [f"# {plat['name']} — chapters read from a RENDERED page.",
             "#",
             "# This platform serves a shell and builds its chapter list in JavaScript, so a fetch",
             "# returns nothing to parse. The page is rendered with headless chromium and the DOM",
             "# it produced is read — the platform's own page, as it chose to draw it.",
             "#",
             "# date_basis: rendered — weaker than a feed the platform published, stronger than a",
             "# pattern matched in static markup. No genre label is established here (§4).",
             "source: webpages", f"platform: {plat['id']}", f"platform_name: {js(plat['name'])}",
             f"publisher: {js(plat.get('publisher', ''))}", f"retrieved: {a.retrieved}",
             "record_type: web_work_chapters", "identification_mode: discovery-candidate",
             "date_basis: rendered", "date_confidence: reported", "works:"]
        for w in rows:
            L.append(f"  - work_title: {js(w['work_title'])}")
            if w.get("author"):
                L.append(f"    author: {js(w['author'])}")
            L.append(f"    url: {js(w['url'])}")
            L.append(f"    chapter_count: {len(w['episodes'])}")
            L.append("    chapters:")
            for e in w["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                L.append(f"        updated: {e['updated']}")
                if e.get("access_modes"):
                    L.append(f"        access_modes: {js(e['access_modes'])}")
                if e.get("price"):
                    L.append(f"        access_note: {js('point price ' + e['price'])}")
                elif e.get("access_note"):
                    L.append(f"        access_note: {js(e['access_note'])}")
                L.append("        date_basis: rendered")
        L.append("")
        (out / f"rendered-{plat['id']}.yaml").write_text("\n".join(L))
        n = sum(len(w["episodes"]) for w in rows)
        print(f"{plat['name'][:20]:22} works={len(rows):3} chapters={n:4}"
              f"{('  ' + str(dict(failed))) if failed else ''}")


if __name__ == "__main__":
    main()
