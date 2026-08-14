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
                    --cache $YURI_CACHE/render-cache --retrieved 2026-08-01
"""
import argparse, html as _html, json, pathlib, re, subprocess, sys, time
from collections import Counter

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import checkstate  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import schedule_text  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "recon"))
from extract import (CHAPTERISH, norm_date, try_jsonld, try_markup,  # noqa: E402
                     try_next, try_pairs)

CHECKS = {}
CHROME = None
for c in ("/snap/bin/chromium", "/usr/bin/chromium", "/usr/bin/chromium-browser",
          "/usr/bin/google-chrome"):
    if pathlib.Path(c).exists():
        CHROME = c
        break

UA = "Mozilla/5.0 (compatible; yurarium/0.1; +https://yurarium.github.io/)"
BUDGET_MS = 20000   # pixiv builds its episode list late; 8000 lost ~28 works to timing
PAUSE = 1.0
MIN_EPISODES = 2


#: HOW LONG A RENDERED PAGE IS WORTH REUSING, weighed against how often this actually runs. At two
#: days, a run three days after the last one re-rendered every page: the cache had been saved, was
#: restored, and every entry in it was stale by a day. That is 24 minutes of browser time thrown
#: away for a chapter list that changes weekly at most. A chapter this misses is picked up by the
#: feed adapters, which are never served stale; what a render supplies is the per-chapter ACCESS
#: state, and a week-old answer to that is worth more than no answer.
RENDER_AGE_DAYS = 7


def render(url, cache, max_age_days=RENDER_AGE_DAYS):
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
ACCESS_BADGE = {"free": ["free"], "ticket-free": ["free-timed"], "point": ["purchase"]}

STRUCTURED = {
    # マガポケ: <li class="c-episode-items__item"> … __date, __ttl, and an icon that is either
    # __ico--free or __ico--point with a price on it.
    "magapoke": {
        "item": r'<li class="c-episode-items__item">',
        "date": r'__date">([^<]*)<',
        "title": r'__ttl">([^<]*)<',
        "access": r'__ico--([\w-]+)">([^<]*)<',
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
            # Three badges, not two. マガポケ marks a chapter --free, --point with a price, or
            # --ticket-free, which is 作品チケット: readable now, without paying, by spending a ticket
            # the platform hands out. That is free-timed and it is most of the middle of every long
            # series here — 念願の悪役令嬢's 第95話 through 第97話, アイドラトリィ's #42 through #44.
            #
            # It was invisible twice over. The capture was (\w+), and '-' is not a word character,
            # so --ticket-free captured as "ticket"; and anything that was not exactly "free" was
            # called purchase. So the one state that means "you can read this right now" was being
            # recorded as the one that means you cannot.
            row["access_modes"] = ACCESS_BADGE.get(kind, ["purchase"])
            if kind == "point" and ico.group(2).strip():
                row["price"] = ico.group(2).strip()
        out.append(row)
    return out


PX_ANCHOR = re.compile(r'<a href="/viewer/stories/(\d+)">(.*?)</a>', re.S)
# pixiv puts the author in a plain <div> immediately after the work's <h1> — no class, no link.
# author_near_title() cannot see it, which is why 腹割るウチらの秘密ごと! came back without one.
PX_AUTHOR = re.compile(r"<h1[^>]*>[^<]*</h1>\s*<div[^>]*>([^<]{1,30})</div>")
PX_DATE = re.compile(r"更新日[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日")


def episodes_pixiv(html):
    """pixivコミック's episode list, which the generic strategies cannot see.

    Each episode is an <a href="/viewer/stories/<id>"> holding three text nodes: a label, a
    subtitle, and 更新日: 2026年5月8日. The label is usually a bare number — pixiv numbers 1, 2, 3 —
    which is why CHAPTERISH never matched it and why this platform came back with a fraction of its
    chapters. On anthologies the label is the artist instead (漫画：樫風), so it is taken as written
    rather than parsed.

    Access: the rendered list holds exactly the episodes a signed-out reader can open. Checked
    against the four works whose per-episode access was independently known — 3 free of 18, 7 of 7,
    1 of 42, 5 of 10 — and the anchor count matched the free count every time. So membership of
    this list IS the access statement, the same way GigaViewer's ?free_only=1 feed is. It is a
    statement about what is free, and says nothing about the rest, which is why the paid episodes
    are absent here rather than recorded as purchase.
    """
    out, seen = [], set()
    for sid, block in PX_ANCHOR.findall(html):
        d = PX_DATE.search(block)
        if not d:
            continue                       # 最初から読む and other furniture: no date, not an episode
        parts = [x.strip() for x in
                 _html.unescape(re.sub(r"<[^>]+>", "\n", block)).split("\n") if x.strip()]
        # Strip the date fragment rather than dropping the whole node: on some works the subtitle
        # and 更新日 share a text node, and dropping it took the subtitle with it — leaving
        # 怪獣ロマンティクス's chapter as "…別れは出会いのシグナル 更新日:".
        parts = [re.sub(r"\s*更新日.*$", "", x).strip() for x in parts]
        parts = [x for x in parts if x]
        if not parts or sid in seen:
            continue
        seen.add(sid)
        out.append({"title": " ".join(parts[:2]),
                    "updated": f"{int(d.group(1)):04d}-{int(d.group(2)):02d}-{int(d.group(3)):02d}",
                    "access_modes": ["free"]})
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


def text_of(html):
    """The DOM as a reader sees it. The schedule is prose on the page, not markup."""
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", html or "", flags=re.S | re.I)
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", t)))


def carry_over(path, rows):
    """Fold this run's rows into whatever the file already holds, keyed on URL.

    WHY THIS EXISTS. --limit-per-host bounds what one run costs, and the writer replaced the whole
    file with just that window. pixivコミック has 131 targets and a limit of 40, so a run kept the
    40 it happened to reach and silently dropped the other 91: the file went from 103 works and 446
    chapters to 35 and 155, and 13 claims that had been attested became untraced again. The limit
    is right; overwriting is what was wrong.

    A work read this time replaces its earlier entry, because a fresh reading of the same page is
    better evidence than an old one. A work not reached this time is kept as it was, because not
    looking at a page is not the same as finding nothing on it.
    """
    keep = []
    if path.exists():
        old = yaml.safe_load(path.read_text()) or {}
        fresh = {w["url"] for w in rows if w.get("url")}
        keep = [w for w in (old.get("works") or []) if w.get("url") not in fresh]
    return keep

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

    # Loaded once for the whole run; a per-work save would rewrite the file 188 times.
    global CHECKS
    CHECKS = checkstate.load()
    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    spec = yaml.safe_load(open(a.targets)) or {}
    for plat in spec.get("platforms") or []:
        rows, failed = [], Counter()
        # SAYING WHAT IT IS DOING, because this stage was silent for 24 minutes. A browser render is
        # ten seconds and this walks a hundred of them, so a run that has hung and a run that is
        # working looked exactly alike from outside: one line per platform, before the work starts.
        want = (plat.get("works") or [])[: a.limit_per_host]
        print(f"{plat.get('name') or plat.get('platform') or '?':22} rendering {len(want)} work(s)"
              f" (cached renders are reused for {RENDER_AGE_DAYS} days)", flush=True)
        for t in want:
            try:
                html = render(t["url"], cache)
            except subprocess.TimeoutExpired:
                failed["timeout"] += 1
                continue
            if not html:
                failed['empty render'] += 1
                # Chromium ran the page and it produced nothing. Recorded as a look, because it is one:
                # a claim on this work is not waiting for somebody to go and check.
                checkstate.record(CHECKS, plat['name'], t.get('title') or '', 'blocked',
                                  note='rendered; the page yielded no DOM to read')
                continue
            spec = STRUCTURED.get(plat["id"])
            if plat["id"] == "pixivcomic":
                # No generic fallback here. A pixiv work with one chapter is an ordinary new
                # serialisation, and falling through to the generic extractor on that basis is what
                # gave 怪獣ロマンティクス a chapter called "300話以上✨】無料でたっぷり読める人気作品を…"
                # — a promotional banner, scraped because the real parser had "too few" rows.
                eps = episodes_pixiv(html)
            else:
                eps = episodes_structured(html, spec) if spec else []
                if len(eps) < MIN_EPISODES:
                    eps = episodes(html)
            if len(eps) >= MIN_EPISODES:
                row = {"work_title": t.get("title"), "url": t["url"], "episodes": eps}
                au = None
                if plat["id"] == "pixivcomic":
                    m_au = PX_AUTHOR.search(html)
                    au = m_au.group(1).strip() if m_au else None
                au = au or author_near_title(html, t.get("title"))
                if au:
                    row["author"] = au
                # WHAT THE PAGE SAYS ABOUT ITSELF. Read from the same DOM as the episodes, because
                # it is the answer to the question the episode dates only hint at: this platform
                # shows a rolling window of free chapters, so a run that looks stopped may simply
                # be one whose free window has moved on. See render/schedule_text.py.
                sched = schedule_text.read(text_of(html), a.retrieved)
                if sched:
                    row["stated_schedule"] = sched
                rows.append(row)
                # A SUCCESSFUL READ IS THE THING WORTH RECORDING, and only failures were. The
                # ledger holds `last_checked`, `schedule.py` sorts by how long ago that was, and a
                # work with no row at all returns None, which sorts FIRST as most overdue. So every
                # work we read cleanly looked maximally stale and every work that failed looked
                # freshly seen. アイ・ヘイ・チュー published on 2026-08-07, was read without trouble,
                # and was still listed overdue on the 8th because success left no trace.
                checkstate.record(CHECKS, plat['name'], t.get('title') or '', 'ok',
                                  note=f'rendered; {len(eps)} episode(s) read')
            else:
                failed['no dated chapters'] += 1
                # A FINDING, not a failure. The page rendered and the platform drew no dates on it,
                # so a reader on the site cannot see when a chapter appeared either. Recorded, or a
                # claim against this work reads as one nobody has looked at.
                checkstate.record(CHECKS, plat['name'], t.get('title') or '', 'empty',
                                  note='rendered; the platform draws no dates on this page')

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
            if w.get("stated_schedule"):
                L.append("    stated_schedule:")
                for k2, v2 in sorted(w["stated_schedule"].items()):
                    L.append(f"      {k2}: {js(v2)}")
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
        # Everything this run did not reach, written back unchanged. See carry_over.
        path = out / f"rendered-{plat['id']}.yaml"
        kept = carry_over(path, [{"url": w["url"]} for w in rows])
        for w in kept:
            L.append(f"  - work_title: {js(w.get('work_title', ''))}")
            if w.get("author"):
                L.append(f"    author: {js(w['author'])}")
            L.append(f"    url: {js(w.get('url', ''))}")
            L.append(f"    chapter_count: {len(w.get('chapters') or [])}")
            L.append("    chapters:")
            for e in (w.get("chapters") or []):
                L.append(f"      - title: {js(e.get('title', ''))}")
                L.append(f"        updated: {e.get('updated')}")
                if e.get("access_modes"):
                    L.append(f"        access_modes: {js(e['access_modes'])}")
                if e.get("access_note"):
                    L.append(f"        access_note: {js(e['access_note'])}")
                L.append(f"        date_basis: {e.get('date_basis', 'rendered')}")
        L.append("")
        path.write_text("\n".join(L))
        n = sum(len(w["episodes"]) for w in rows)
        print(f"{plat['name'][:20]:22} works={len(rows):3} chapters={n:4}"
              f"{f'  (+{len(kept)} carried over)' if kept else ''}"
              f"{('  ' + str(dict(failed))) if failed else ''}")

    checkstate.save(CHECKS)


if __name__ == "__main__":
    main()
