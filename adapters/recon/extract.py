#!/usr/bin/env python3
"""Second-pass reconnaissance: try to actually extract dated chapters (REQUIREMENTS §6).

The first pass asked "is a date on this page". That question has a false-positive answer —
ガンガンONLINE is server-rendered and shows 2024.05.24発売！, which is a 単行本 release date while
its chapter list loads client-side. Sniffing for date-shaped strings cannot tell the two apart.

So this pass tries the extraction instead, and reports what came back. A strategy counts as working
only if it yields at least two entries that each have a date AND a chapter-like label, because one
dated thing on a page is usually the volume.

Strategies, cheapest first:

  jsonld  — schema.org objects carrying datePublished/dateModified alongside a name.
  next    — __NEXT_DATA__, walked for arrays of objects with both a date-ish and a title-ish key.
  nuxt    — window.__NUXT__, same walk over whatever JSON can be recovered from the assignment.
  markup  — repeated sibling blocks each containing a date and an anchor. The fallback, and the
            one that needs a per-host selector, so it reports the tag/class it keyed on.

Output feeds data/coverage/extract.yaml, which is the registry a generic adapter reads.

Usage:  extract.py --targets data/coverage/recon-targets.yaml --out data/coverage --retrieved DATE
"""
import argparse, json, pathlib, re, socket, sys, time, urllib.error, urllib.request
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.0
TIMEOUT = 25

DATE_KEY = re.compile(r"(date|updated|published|created|delivery|release|start|open)", re.I)
TITLE_KEY = re.compile(r"(title|name|subtitle|label|heading)", re.I)
# A chapter says so: 第N話, N話, #N, episode N, or a plain number in a numbering context.
# THE COUNTER WORD IS THE WORK'S OWN CHOICE, and every one this misses is a platform that reads as
# having no chapter list. おやすみシェヘラザード counts in 夜, one night per instalment, so やわらか
# スピリッツ listed `2018/5/1 第5夜 『アウトレイジ』 を更新しました。` and nothing here matched it:
# the platform was recorded as offering no chapters when what it offers is nights. 話, 回, 章 are
# the ordinary ones; 品, 皿 and 杯 were added the same way, by a work that counted in dishes.
CHAPTERISH = re.compile(
    r"第?\s*[0-9０-９]+\s*(話|回|章|品|皿|杯|夜)|#\s*\d+|"
    r"(?:episode|ep|file|case|act|vol|chapter)\s*\.?\s*\d+|最終(話|回)", re.I)
ISO = re.compile(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})")
# A JAPANESE PLATFORM WRITING ITS DATES IN ENGLISH. ちゃおプラス prints
# <p class="c-episode-item__date">15 Aug 2026</p> beside <h3 class="c-episode-item__ttl">第35話</h3>,
# for all 56 chapters of 上杉くんは女の子をやめたい. Every strategy here finds the date through
# `norm_date`, which knew only the numeric forms, so each block came back with a chapter label and
# no date and every row was dropped. The work was then reported as one no route could reach, which
# is a statement about this pattern rather than about 小学館.
#
# A DAY IS REQUIRED. `May 2024` is a month and a year, and a date guessed out of one would be
# invented (§6). `全56話 Aug 2026` yields nothing, which is the correct answer.
#
# THE CAPITAL IS REQUIRED TOO. A platform printing a date capitalises the month, and accepting a
# lowercase one buys nothing while opening the pattern to English prose that happens to run a
# number into a month name.
MONTHS = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
DMY = re.compile(r"\b([0-3]?\d)\s+([A-Z][a-z]{2})[a-z]*\.?\s+(\d{4})\b")
# 単行本 release dates are the trap this pass exists to avoid.
VOLUMEISH = re.compile(r"発売|刊行|単行本|巻")
# The element a page uses to hold the chapter's own name. マンガPark writes
# <p class="chapterTitle">3話①</p>, ファイアCROSS <span class="shop-item-info-name">第0話</span>,
# マンガよもんが <div class="episode-name">Chapter.3 第1話-3</div>. Requiring the node to hold text
# and nothing else keeps this to the case where the page really has named one element as the title:
# ダ・ヴィンチニュース wraps its heading round an <a>, so it is left to the flat reading below.
TITLE_NODE = re.compile(
    r"<(h[1-6]|p|span|div|a|strong|em|b)\b[^>]*"
    r'(?:class|id|itemprop)="[^"]*(?:title|name|subtitle|heading)[^"]*"[^>]*>([^<>]+)</\1>', re.I)
# A text node that is a number and nothing else. It is a like count, a comment count, a price or a
# position, and it is never a chapter label, because CHAPTERISH needs 話/回/#/episode beside the
# digits. Dropping these nodes cannot remove the label, which is why the counts are cut here rather
# than off the end of the assembled title: 'EPISODE 30' is one node, so its 30 survives, while
# マンガPark's 26 and 8 are nodes of their own and do not.
COUNTER_NODE = re.compile(r"^[0-9０-９][0-9０-９,，.]*$")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read(1_500_000).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout,
            ConnectionError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


def norm_date(v):
    s = str(v)
    m = ISO.search(s)
    if m:
        y, mo, d = (int(x) for x in m.groups())
    else:
        # THE NUMERIC FORM FIRST, ALWAYS. A block can hold both, and the one the platform wrote
        # against the chapter is the numeric one everywhere it appears.
        m = DMY.search(s)
        if not m:
            return None
        mo = MONTHS.get(m.group(2).lower())
        if not mo:
            return None
        d, y = int(m.group(1)), int(m.group(3))
    if not (1990 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def entries_from_obj(root):
    """Objects carrying both a date-ish and a title-ish field, at any depth."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            dk = [k for k in o if DATE_KEY.search(k) and norm_date(o[k])]
            tk = [k for k in o if TITLE_KEY.search(k) and isinstance(o[k], str) and o[k].strip()]
            if dk and tk:
                out.append({"title": o[tk[0]].strip()[:80], "date": norm_date(o[dk[0]]),
                            "date_key": dk[0]})
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(root)
    return out


def try_jsonld(html):
    out = []
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            out += entries_from_obj(json.loads(m.group(1)))
        except Exception:                                          # noqa: BLE001
            continue
    return out


def try_next(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return []
    try:
        return entries_from_obj(json.loads(m.group(1)))
    except Exception:                                              # noqa: BLE001
        return []


def try_nuxt(html):
    """__NUXT__ is an assignment, often an IIFE. Only the plain-object form is recoverable here;
    anything else is left to the markup strategy rather than evaluated."""
    m = re.search(r"window\.__NUXT__\s*=\s*(\{.*?\});?\s*</script>", html, re.S)
    if not m:
        return []
    try:
        return entries_from_obj(json.loads(m.group(1)))
    except Exception:                                              # noqa: BLE001
        return []


def try_labels(html, page_url=""):
    """Chapter labels a page lists while stating no date for any of them.

    THE PLATFORMS THIS EXISTS FOR PUBLISH NO DATES AT ALL. コミックエッセイ劇場 lists ten 第N話
    entries and prints no date on the listing, on the episode pages, in its metadata or in its
    JSON-LD, which is a breadcrumb; てれびくんヒーローコミックス lists eleven the same way. Every
    other extractor here pairs a label with a date and drops a label that has none, so both
    platforms read as having no chapter list rather than no dates, and neither was read at all.
    Web漫画速報 and やわらかスピリッツ are the same shape one work at a time.

    A DATE IS STILL NOT INVENTED. What comes back carries no date, and the caller supplies the day
    it read the page: `build.py` locks a heuristic date at first sighting, which is REQUIREMENTS §5
    and is exactly what ヤンジャン+ already gets for a page that states none.

    ANCHORS ONLY, because a chapter a reader can open is a link. A heading that names the work, a
    banner and a promotion are not, which is what keeps this from reading a page's furniture as a
    chapter list.

    AND UNDER THIS WORK'S OWN ADDRESS, which is what keeps it from reading somebody else's. マンガ
    ボックス puts a carousel of other serials on every reader page and 53 chapter labels came back
    for a work that has none of them: `38話 放課後インスタントXXX` is a different work's thirty-
    eighth chapter. A chapter of this work lives under this work's address, so the key segment of
    the page's own URL has to appear in the link.
    """
    key = ""
    for part in reversed([s for s in str(page_url or "").split("?")[0].split("/") if s]):
        if len(part) > 3 and part not in ("http:", "https:", "index.html"):
            key = part.replace(".html", "")
            break
    out, seen = [], set()
    for m in re.finditer(r"<a\b[^>]*href=\"([^\"]*)\"[^>]*>(.*?)</a>", html, re.S | re.I):
        href, body = m.group(1), m.group(2)
        # A RELATIVE LINK IS ALREADY UNDER THIS WORK'S ADDRESS. てれびくんヒーローコミックス writes
        # its chapters as `episode-010/`, which the browser resolves against the work's own path
        # and which carries no key to match: requiring the key threw away every chapter it has.
        # What the rule refuses is a link that goes somewhere ELSE, so an absolute one that does
        # not name this work is the only kind to drop.
        absolute = href.startswith(("http://", "https://", "//", "/"))
        if key and absolute and key not in href:
            continue
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()
        if not text or len(text) > 60 or not CHAPTERISH.search(text):
            continue
        # THE LABEL AND NOT THE SENTENCE AROUND IT. A card links its whole blurb, so the anchor's
        # text can carry the work's title and a strapline with the chapter buried in the middle.
        c = CHAPTERISH.search(text)
        label = text[max(0, c.start() - 4): c.end() + 40].strip(" 　·・|/-")
        if label in seen:
            continue
        seen.add(label)
        out.append({"title": label, "date": None})
    return out


def try_pairs(html):
    """Pair each date with the nearest chapter label before it.

    try_markup splits at every occurrence of a tag, which yields the fragment between one opening
    tag and the next rather than a nested container. On a flat <li> list that is the same thing; on
    a nested div tree it is not, and title and date land in different fragments. マンガワン renders
    its chapter list as nested divs — 第8話(後編) in one <p>, 2026/07/19 in another two levels down
    — so nothing was extracted from a page that plainly had it.

    Pairing by position needs no assumption about structure at all.
    """
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    flat = re.sub(r"<[^>]+>", "\x00", body)
    out, seen = [], set()
    for m in re.finditer(r"\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}", flat):
        d = norm_date(m.group(0))
        if not d:
            continue
        back = flat[max(0, m.start() - 900): m.start()]
        labels = list(CHAPTERISH.finditer(back))
        if not labels:
            continue
        lm = labels[-1]
        # If another date sits between the label and this one, the label belongs to that date and
        # not to this — 第8話(後編) was being paired with 第8話(前編)'s date as well as its own.
        if re.search(r"\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}", back[lm.end():]):
            continue
        label = re.sub(r"[\x00]+", " ", back[lm.start(): lm.end() + 40]).strip()
        label = re.split(r"\s{2,}", label)[0].strip()
        # Rendered pages carry comment and sort controls next to the chapter list, and they were
        # ending up inside the label: 「第1話 出遭いのコメント いいね順 新着順 568コメント」.
        label = re.split(r"のコメント|いいね順|新着順|\d+コメント", label)[0].strip()
        if not label or (label, d) in seen:
            continue
        seen.add((label, d))
        out.append({"title": label, "date": d})
    return out


def block_text(b):
    """A block flattened to text, with the nodes that are only a counter left out.

    Tags become node boundaries rather than spaces, so a number the page printed in an element of
    its own stays separable from the label next to it. That boundary is the whole difference
    between '3話① 26 8' and '3話①'."""
    parts = [re.sub(r"\s+", " ", s).strip() for s in re.split(r"<[^>]+>", b)]
    return " ".join(p for p in parts if p and not COUNTER_NODE.match(p))


def named_title(b):
    """The text of the block's own title element, when it holds a chapter label."""
    for m in TITLE_NODE.finditer(b):
        t = re.sub(r"\s+", " ", m.group(2)).strip()
        if t and CHAPTERISH.search(t):
            return t
    return None


def try_markup(html):
    """Repeated blocks holding a date and an anchor. Reports the container it keyed on so the
    result is reproducible as a selector rather than a one-off parse.

    A row carries `exact` when the title came from the page's own title element. Callers must not
    trim such a title: it is the name the publisher wrote, and the trimming they apply to a flat
    run of text would cut a real subtitle."""
    # Commented-out markup is not content. コミックノヴァ leaves a whole promo box for another work
    # in a comment, and it was arriving as the chapter '更新！ 第8話 -->'.
    body = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
    best = []
    for tag in ("li", "article", "div", "tr", "a"):
        blocks = re.split(rf"(?=<{tag}\b)", body)
        found, cls = [], Counter()
        for b in blocks:
            b = b[:4000]
            d = norm_date(re.sub(r"<[^>]+>", " ", b))
            if not d:
                continue
            text = block_text(b)
            if VOLUMEISH.search(text[:160]) and not CHAPTERISH.search(text[:160]):
                continue
            t = CHAPTERISH.search(text)
            if not t:
                continue
            c = re.search(rf'<{tag}[^>]*class="([^"]{{0,60}})"', b)
            if c:
                cls[c.group(1).split()[0]] += 1
            row = {"title": text[:80], "date": d}
            named = named_title(b)
            if named:
                row["title"], row["exact"] = named[:80], True
            found.append(row)
        if len(found) > len(best):
            best = found
            best_tag, best_cls = tag, (cls.most_common(1)[0][0] if cls else "")
    if not best:
        return [], None
    return best, {"tag": best_tag, "class": best_cls}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = (yaml.safe_load(open(a.targets)) or {}).get("targets") or []
    if a.limit:
        rows = rows[: a.limit]

    results = []
    for i, t in enumerate(rows, 1):
        url = t.get("work_url")
        r = {"platform": t["platform"], "host": t["host"], "work_url": url,
             "exclusive_works": t.get("exclusive_works", 0)}
        html = get(url) if url else ""
        if not html:
            r["strategy"] = "no-response"
            results.append(r)
            print(f"[{i}/{len(rows)}] {t['platform'][:20]:22} no-response", flush=True)
            continue
        sel = None
        for name, fn in (("jsonld", try_jsonld), ("next", try_next), ("nuxt", try_nuxt)):
            got = fn(html)
            got = [g for g in got if CHAPTERISH.search(g["title"])] or got
            if len(got) >= 2:
                r["strategy"], r["sample"] = name, got[:3]
                break
        else:
            got, sel = try_markup(html)
            if len(got) >= 2:
                r["strategy"], r["sample"], r["selector"] = "markup", got[:3], sel
            else:
                r["strategy"] = "none"
        results.append(r)
        print(f"[{i}/{len(rows)}] {t['platform'][:20]:22} {r['strategy']}"
              f"{' ' + str(sel) if sel and r['strategy'] == 'markup' else ''}", flush=True)

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "extract.yaml").write_text(
        "# Second-pass reconnaissance: which extraction strategy actually returns dated chapters.\n"
        "# A strategy counts only if it yielded >= 2 entries with both a date and a chapter-like\n"
        "# label — one dated thing on a page is usually the 単行本 release, which is the trap the\n"
        "# first pass fell into on ガンガンONLINE.\n"
        f"source: derived\nrole: reconnaissance\nretrieved: {a.retrieved}\n"
        + yaml.safe_dump({"platforms": results}, allow_unicode=True, sort_keys=False))
    c = Counter(r["strategy"] for r in results)
    print("\n" + ", ".join(f"{k}: {v}" for k, v in c.most_common()))
    print("written:", out / "extract.yaml")


if __name__ == "__main__":
    main()
