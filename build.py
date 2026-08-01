#!/usr/bin/env python3
"""Merge source layers, validate, and compile the published dataset.

Source records (data/source/<source>/) are stored as fetched and never edited. Curation lives in
data/overlay/ and always wins. This step merges them by source priority, enforces the validation
rules in REQUIREMENTS §6, and writes data/build/.

Fails closed: any validation error aborts the build without writing.

Usage:  build.py [--out data/build]
"""
import argparse, datetime, glob, json, pathlib, re, sys, unicodedata
from collections import defaultdict

sys.path.insert(0, "adapters")
from crossplatform import carriage, merge_releases  # noqa: E402

import yaml

# REQUIREMENTS §1. A field whose provenance is not here fails the build.
# Tier A/B attesting sources only. Discovery-only sources (Tier C/D) never appear here — they feed
# data/queue/, which is deliberately outside the source tree so nothing can promote a candidate
# into a record by accident.
ALLOWED_SOURCES = {"madb", "openbd", "ndl", "openbd-jpro", "publisher", "ichijinsha",
                   "gigaviewer", "kadokomi", "comicfuz", "webpages", "comparators", "nicovideo"}

# Sources carrying work-level records that merge into a work. Others (release feeds) are
# platform-level and compile separately.
WORK_SOURCES = {"madb", "openbd", "ndl", "openbd-jpro", "publisher", "ichijinsha"}

# REQUIREMENTS §2. Covers may only be referenced from a publisher-supplied reuse feed.
ALLOWED_COVER_HOSTS = {"cover.openbd.jp"}

# Field-level priority when sources disagree (REQUIREMENTS §1: A > B > C).
PRIORITY = {"madb": 10, "ndl": 10, "openbd": 9, "publisher": 5, "ichijinsha": 5}


def jsonable(o):
    """PyYAML yields datetime.date for full ISO dates; dates are stored as ISO strings."""
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    raise TypeError(f"unserialisable {type(o).__name__}")


# A series ending is its own event, as distinct from an ordinary chapter as a first chapter is.
# Titles state it plainly and in several forms: 最終話 / 最終回 / 最終幕 / 最終エピソード, and a
# trailing （完）. Split finales are common — 最終話①②③, 最終話-1, 最終話前編/後編, 最終話［上］［下］ —
# and every part matches, so a series can carry the label on more than one day. That is left alone:
# each part genuinely is part of the ending, and picking one as the "real" last would be a guess.
FINAL_RE = re.compile(r"最終(話|回|幕|エピソード)|[（(]完[）)]\s*$")
# Announcements and artwork typed as chapters upstream — they are not story instalments.
NON_STORY_RE = re.compile(r"告知|お知らせ|カバー|PV|特報|予告|特典|コミックス第[0-9０-９]+巻|重版")
# Extras and side stories count on the CHAPTER side: おまけ, 番外編 and 外伝 are content a reader
# follows the series for, unlike an announcement or a cover reveal. They are instalments of an
# existing work, so they are never a new series either.
EXTRA_RE = re.compile(r"おまけ|番外編|外伝|特別編|幕間")
# Things platforms file among the chapters that are not instalments. Grouped here because they all
# get the SAME treatment: judged against how often the series itself uses the marker, never as a
# flat keyword rule (see the outlier test below).
#
# Three kinds, found by surveying the titles that carry no chapter number across the whole corpus
# rather than by guessing at a vocabulary:
#   volume promotion — 3巻発売フェア, 第2巻 書店フェア, 単行本
#   bonus artwork    — オフショット (91 occurrences), イラスト (52)
#   notices          — 休載 (18)
NON_STORY_OUTLIER_RE = re.compile(
    r"[0-9０-９一二三四五六七八九十]+\s*巻|発売|フェア|刊行|書店|単行本"
    r"|オフショット|イラスト|休載")
VOLUME_MARK_RE = NON_STORY_OUTLIER_RE   # retained: the name the outlier test was written against
_KANJI = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9}


def kanji_number(s):
    """Kanji numerals 1–99 — 第十一話 is chapter 11. Titles using them were falling to `unknown`."""
    m = re.search(r"[一二三四五六七八九十]+", s or "")
    if not m:
        return None
    k = m.group(0)
    if "十" not in k:
        return _KANJI.get(k) if len(k) == 1 else None
    tens, _, ones = k.partition("十")
    return (_KANJI.get(tens, 1) if tens else 1) * 10 + (_KANJI.get(ones, 0) if ones else 0)


def ep_number(title):
    """Chapter number where the title states one.

    Platforms number chapters many ways: 第7話 / 7話 / #7 / その7 / File.30 / Episode 12 /
    Case.4 / act.9, plus full-width digits. Missing these left obvious chapters as `unknown`.
    """
    import unicodedata
    s = unicodedata.normalize("NFKC", title or "")
    pats = [
        r"(?:第|#|その)\s*(\d+)\s*(?:話|回|章)?",
        r"^\s*(\d+)\s*(?:話|回|章)",
        r"(?:file|episode|ep|case|act|track|phase|stage|page|scene)\s*[.．]?\s*(\d+)",
        # Works that count in their own units: 2皿目, 5杯目, 3夜, 7手目, 27枠目, 17輪目 …
        # 巻 is deliberately absent: a leading N巻 is usually a volume, not a chapter number.
        r"^\s*(\d+)\s*[皿杯品夜手戦局曲片粒滴枠輪服着球]\s*目?",
    ]
    for pat in pats:
        m = re.search(pat, s, re.I)
        if m:
            return int(m.group(1))
    if re.search(r"第[一二三四五六七八九十]+[話回章]", s):
        return kanji_number(s)
    return None


def norm_work(s):
    """Normalise a work title for comparison.

    NFKC first. Without it （私に） and (私に) compare unequal, as do ２ and 2, and ！ and !.
    That duplicated series in the feed. The comparators and the platforms render all of these
    inconsistently, so folding them is the only way titles match across sources.

    The long vowel mark ー is deliberately NOT stripped: it is a letter in katakana, not
    punctuation, and removing it would merge genuinely different titles.
    """
    s = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", s or "")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"""[\s\-.=、。･・!?,:;'"“”‘’()\[\]{}「」『』【】〈〉《》〔〕~〜_/\\|+*&#@]""",
                  "", s.strip().lower())


def load_dir(p):
    return [yaml.safe_load(open(f)) for f in sorted(glob.glob(f"{p}/*.yaml"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/build")
    a = ap.parse_args()

    src = defaultdict(dict)
    for d in sorted(glob.glob("data/source/*")):
        name = pathlib.Path(d).name
        if name not in ALLOWED_SOURCES:
            sys.exit(f"VALIDATION: source directory '{name}' is not on the allowlist (§1)")
        if name not in WORK_SOURCES:
            continue
        for r in load_dir(d):
            wid = r["work_id"]
            if name in src[wid]:
                sys.exit(f"VALIDATION: duplicate work_id '{wid}' within source '{name}'. "
                         "Ids must be unique; a collision silently merges distinct works.")
            src[wid][name] = r

    overlay = {r["work_id"]: r for r in load_dir("data/overlay")} if pathlib.Path("data/overlay").exists() else {}

    works, errors, warnings = [], [], []
    for wid, by_source in sorted(src.items()):
        base = by_source.get("madb")
        if not base:
            errors.append(f"{wid}: no primary (madb) record")
            continue
        ov = overlay.get(wid, {})

        w = {
            "work_id": wid,
            "title": base["title"],
            "creator": base.get("creator", ""),
            "publisher": base.get("publisher", ""),
            "imprint": base.get("imprint", ""),
            "volume_count": base.get("volume_count", 0),
            "grouping": base.get("grouping"),
            "sources": sorted(by_source),
        }

        # Volume-level merge: openBD confirms dates and may supply a cover reference.
        enrich = {v["isbn"]: v for v in (by_source.get("openbd", {}).get("volumes") or []) if v.get("isbn")}
        vols = []
        for v in base.get("volumes") or []:
            o = enrich.get(v.get("isbn", ""), {})
            m = {k: (str(v[k]) if k == "published" else v[k]) for k in ("madb_id", "number", "isbn", "published") if k in v}
            if o.get("published") and o["published"] != v.get("published"):
                # Keep the higher-priority value; record rather than discard the disagreement (§1).
                m["published_openbd"] = o["published"]
            if o.get("cover_url"):
                m["cover_url"] = o["cover_url"]
            m["openbd"] = "present" if o else "absent"
            vols.append(m)
        w["volumes"] = vols

        # first_publication is the inclusion test and is required (DEFINITIONS §6). What we can
        # attest here is the first 単行本; magazine serialisation is not in the bulk data, so the
        # record says so rather than implying the tankōbon was the original appearance.
        # Take the earliest attested volume date. MADB leads; where it has no date, openBD supplies
        # one, and the record says which source it came from rather than blurring them together.
        # PyYAML turns a full ISO date into datetime.date but leaves YYYY-MM a string, so every
        # date is coerced before comparison or the sort raises on mixed types.
        dated = [(str(v["published"]), "madb") for v in vols if v.get("published")]
        dated += [(str(v["published_openbd"]), "openbd") for v in vols if v.get("published_openbd")]
        dated += [(str(o["published"]), "openbd") for o in enrich.values()
                  if o.get("published") and not any(v.get("published") for v in vols if v.get("isbn") == o.get("isbn"))]
        if dated:
            date, via = min(dated)
            w["first_publication"] = {
                "date": date,
                "date_source": via,
                "venue": base.get("imprint", "") or base.get("publisher", ""),
                "venue_type": "tankobon-imprint",
                "country": "JP",
                "note": "First known 単行本. Magazine serialisation not attested by current sources.",
            }
        else:
            errors.append(f"{wid}: missing first_publication (DEFINITIONS §6) — no date in any source")

        # Classification. marketing_label is mechanical; content_tier is never automated (§6).
        for axis in ("marketing_label", "content_tier"):
            val = ov.get(axis, base.get(axis))
            basis = ov.get(f"{axis}_basis", base.get(f"{axis}_basis"))
            if val is None:
                continue
            if not basis:
                errors.append(f"{wid}: {axis}={val} has no basis (DEFINITIONS §5)")
                continue
            if basis.get("source") not in ALLOWED_SOURCES:
                errors.append(f"{wid}: {axis} basis source '{basis.get('source')}' not on allowlist (§1)")
            w[axis] = val
            w[f"{axis}_basis"] = basis

        if not w.get("marketing_label") and not w.get("content_tier"):
            errors.append(f"{wid}: fails the inclusion test — neither axis set (DEFINITIONS §2)")

        # Media policy (§2): covers only from a permitted host, never on explicit records.
        explicit = bool(ov.get("explicit_content"))
        w["explicit_content"] = explicit
        for v in vols:
            u = v.get("cover_url")
            if not u:
                continue
            host = u.split("/")[2] if "://" in u else ""
            if host not in ALLOWED_COVER_HOSTS:
                errors.append(f"{wid}: cover host '{host}' is not a publisher-supplied reuse feed (§2)")
            if explicit:
                errors.append(f"{wid}: cover referenced on an explicit_content record (§2)")

        if w.get("content_tier") is None:
            warnings.append(wid)
        works.append(w)

    # Append-and-mark (§4): the build never shrinks silently.
    out = pathlib.Path(a.out)
    prev = out / "works.json"
    if prev.exists():
        before = len(json.loads(prev.read_text())["works"])
        if len(works) < before:
            errors.append(f"record count fell {before} -> {len(works)}; deletion requires a takedown "
                          f"record (§4). Refusing to write.")

    if errors:
        print(f"BUILD FAILED — {len(errors)} validation error(s):", file=sys.stderr)
        for e in errors[:25]:
            print("  ✗", e, file=sys.stderr)
        if len(errors) > 25:
            print(f"  … and {len(errors)-25} more", file=sys.stderr)
        sys.exit(2)

    out.mkdir(parents=True, exist_ok=True)
    (out / "works.json").write_text(json.dumps(
        {"count": len(works), "works": works}, ensure_ascii=False, indent=1, default=jsonable))

    # Search index: only what the list view needs, so the initial payload scales with works
    # rather than with total volume history (§5).
    idx = [{"id": w["work_id"], "t": w["title"]["ja"], "y": w["title"].get("yomi", ""),
            "c": w.get("creator", ""), "n": w["volume_count"],
            "d": w.get("first_publication", {}).get("date", ""),
            "l": w.get("marketing_label"), "ct": w.get("content_tier"),
            "g": w.get("grouping")} for w in works]
    (out / "index.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":"), default=jsonable))

    if len(works) != len(src):
        sys.exit(f"VALIDATION: {len(src)} work ids in, {len(works)} out — records lost in merge.")
    # ---- Web releases (§5) -------------------------------------------------------------------
    releases, platforms = [], []
    for f in sorted(glob.glob("data/source/gigaviewer/*.yaml")):
        d = yaml.safe_load(open(f)) or {}
        if d.get("record_type") in ("web_series", "print_candidates"):
            continue
        pid = d.get("platform")
        platforms.append({"id": pid, "name": d.get("platform_name"),
                          "publisher": d.get("publisher"),
                          "series": d.get("yuri_series_count", 0),
                          "retrieved": str(d.get("retrieved", ""))})
        for r in d.get("releases") or []:
            releases.append({
                "id": r.get("release_id"), "work": r.get("work_title"),
                "ep": r.get("episode_title"), "type": r.get("release_type"),
                "adv": bool(r.get("advances_narrative")),
                # Series whose entire output is 試し読み are promoting a printed volume, not
                # publishing web manga (§5). Carried, but not shown as releases by default.
                "web": r.get("web_status", "serialised"),
                # `date` is the earliest evidence held, locked when the release was first seen
                # and never revised (§5). Platforms mass-update Atom <updated> on refresh and
                # import, so their current value is carried for reference, never as the sort key.
                "pub": str(r.get("date") or r.get("platform_updated", ""))[:10],
                "seen": str(r.get("first_seen", "")),
                "basis": r.get("date_basis", "bootstrap"),
                "conf": r.get("date_confidence", "reported"),
                "why": r.get("date_note", ""),
                "moved": r.get("platform_date_changed", ""),
                "url": r.get("url"),
                "author": r.get("author", ""), "plat": pid,
                "plat_name": d.get("platform_name"),
                "ident": r.get("identified_via", "platform-genre"),
                "free_from": str(r.get("free_term_start", "")) or None,
            })
    # COMIC FUZ publishes no feed, so its adapter returns full chapter histories rather than a
    # rolling window. Only recent chapters join the feed — the rest stay in the source layer, where
    # they are the project's only real access_modes data.
    # Other platforms' Atom feeds hold roughly a fortnight of updates. FUZ returns full histories,
    # so its contribution is trimmed to a comparable window or it dominates the feed.
    # One window for everything that enters the feed. The platform windows used to be 21 days while
    # the comparator claims ran to 60, which meant the feed showed two months of "site says this
    # updated" against three weeks of "the publisher confirms it" — so a claim older than 21 days
    # could never be superseded by the chapter it duplicated, and every such work was counted a
    # miss. クレアちゃん飼育日記 was reported missing while its chapter sat in the source layer one
    # day the wrong side of the cutoff.
    FEED_DAYS = 60
    FUZ_FEED_DAYS = FEED_DAYS
    fuz_ahead = {}
    fz = pathlib.Path("data/source/comicfuz/works.yaml")
    if fz.exists():
        d = yaml.safe_load(fz.read_text()) or {}
        # Anchor the window to TODAY, not to the newest date in the data. FUZ carries free dates
        # for chapters running ahead of the free line, and anchoring on those pulled months of
        # back-catalogue into the feed.
        today = str(datetime.date.today())
        cutoff = str(datetime.date.today() - datetime.timedelta(days=FUZ_FEED_DAYS))
        for w in d.get("works") or []:
            for c in w.get("chapters") or []:
                u = str(c.get("updated") or "")
                # An advance chapter has no `updated` at all — FUZ states no publication date for
                # it, only when it stops costing points — so there is no date to file it under.
                # It is attached to the work below instead of being given an invented one.
                if not u or u < cutoff or u > today or c.get("advance_paid"):
                    continue
                releases.append({
                    "id": f"comicfuz:{c.get('chapter_id')}", "work": w.get("work_title"),
                    "ep": c.get("title"), "type": "chapter", "adv": True,
                    "web": "serialised", "pub": u, "seen": str(d.get("retrieved", "")),
                    "basis": "bootstrap", "conf": "reported", "why": "", "moved": "",
                    "url": (f"https://comic-fuz.com/manga/viewer/{c['chapter_id']}"
                            if c.get("chapter_id") else w.get("url")),
                    "series_url": w.get("url"),
                    "author": ", ".join(w.get("authors") or []),
                    "plat": "comic-fuz", "plat_name": "COMIC FUZ",
                    "ident": "discovery-candidate", "free_from": None,
                    "access_modes": c.get("access_modes") or [],
                    "became_free": bool(c.get("became_free")),
                    "access_changed": c.get("access_changed"),
                    # FUZ's dates track the free schedule rather than publication, so a FUZ row is
                    # "this became readable free on this date". A row still carrying `purchase` is
                    # one whose free window has since closed; it is an update, but not a free one.
                    "date_means": "free-from",
                })
        # Chapters running ahead of the free line. These are published and paid now, and FUZ
        # states when each stops costing points but never when it was published — so they are
        # attached to the work as context rather than emitted as dated rows.
        #
        # This replaces an inferred "paywall window slide" that used to live here, which guessed
        # the flip date from chapter cadence. The guess is unnecessary now that the schedule is
        # read directly, and it was the source of the only 無料化 the feed ever showed.
        for w in d.get("works") or []:
            adv_ch = [c for c in (w.get("chapters") or []) if c.get("advance_paid")]
            if not adv_ch:
                continue
            adv_ch.sort(key=lambda c: str(c.get("free_from") or ""))
            nw = norm_work(w.get("work_title") or "")
            fuz_ahead[nw] = {
                "n": len(adv_ch),
                "ep": adv_ch[0].get("title"),
                "free_from": str(adv_ch[0].get("free_from") or ""),
                "newest_ep": adv_ch[-1].get("title"),
            }

        # A chapter that has flipped to free is an update in the free view even if it was
        # published long ago, so it is emitted on the date the flip was observed.
        for w in d.get("works") or []:
            for c in w.get("chapters") or []:
                if not c.get("became_free") or not c.get("access_changed_on"):
                    continue
                releases.append({
                    "id": f"comicfuz-free:{c.get('chapter_id')}", "work": w.get("work_title"),
                    "ep": c.get("title"), "type": "access-change", "adv": False,
                    "web": "serialised", "pub": str(c["access_changed_on"]),
                    "seen": str(d.get("retrieved", "")), "basis": "observed",
                    "conf": "reported", "why": "", "moved": "", "url": w.get("url"),
                    "author": ", ".join(w.get("authors") or []),
                    "plat": "comic-fuz", "plat_name": "COMIC FUZ",
                    "ident": "discovery-candidate", "free_from": None,
                    "access_modes": c.get("access_modes") or [],
                    "became_free": True, "access_changed": c.get("access_changed"),
                })

    # Platforms with no feed, read from their own server-rendered work pages. Like FUZ these
    # return full histories, so only a recent window joins the feed.
    WEBPAGE_FEED_DAYS = FEED_DAYS
    wcut = str(datetime.date.today() - datetime.timedelta(days=WEBPAGE_FEED_DAYS))
    wtoday = str(datetime.date.today())
    # カドコミ: same shape as the webpages adapters, but it does apply a 百合 tag, so its works
    # carry a marketing_label where present.
    kf = pathlib.Path("data/source/kadokomi/chapters.yaml")
    if kf.exists():
        d = yaml.safe_load(kf.read_text()) or {}
        for w in d.get("works") or []:
            for c in w.get("chapters") or []:
                u = str(c.get("updated") or "")
                if not u or u < wcut or u > wtoday:
                    continue
                releases.append({
                    "id": f"kadokomi:{c.get('code')}", "work": w.get("work_title"),
                    "ep": (c.get("title") or "") + (f" {c['subtitle']}" if c.get("subtitle") else ""),
                    "type": "chapter", "adv": True, "web": "serialised", "pub": u,
                    "seen": str(d.get("retrieved", "")), "basis": "bootstrap",
                    "conf": "reported", "why": "", "moved": "",
                    # Deep-link to the chapter where the platform exposes one. Verified pattern:
                    # /detail/<workCode>/episodes/<episodeCode>.
                    "url": (f"{w.get('url')}/episodes/{c['code']}" if c.get("code") and w.get("url")
                            else w.get("url")),
                    "series_url": w.get("url"),
                    "author": ", ".join(w.get("authors") or []),
                    "plat": "kadokomi", "plat_name": "カドコミ",
                    "ident": "platform-genre" if w.get("marketing_label") == "yuri"
                             else "discovery-candidate",
                    "free_from": None, "access_modes": [],
                })

    for f in sorted(glob.glob("data/source/webpages/*.yaml")):
        d = yaml.safe_load(open(f)) or {}
        pid, pname = d.get("platform"), d.get("platform_name")
        for w in d.get("works") or []:
            for c in w.get("chapters") or []:
                u = str(c.get("updated") or "")
                if not u or u < wcut or u > wtoday:
                    continue
                releases.append({
                    "id": f"{pid}:{c.get('url') or c.get('title')}", "work": w.get("work_title"),
                    "ep": c.get("title"), "type": "chapter", "adv": True,
                    "web": "serialised", "pub": u, "seen": str(d.get("retrieved", "")),
                    # A heuristically-parsed date is not the same kind of fact as one a platform
                    # states, and saying so is the whole price of the generic extractor. Carried
                    # through to the feed rather than left in the source layer.
                    "basis": c.get("date_basis") or d.get("date_basis") or "bootstrap",
                    "conf": d.get("date_confidence") or "reported",
                    "why": ("date matched as a pattern in the page, not stated by the platform"
                            if (c.get("date_basis") or d.get("date_basis")) == "heuristic" else ""),
                    "moved": "",
                    "url": c.get("url") or w.get("url"), "author": "",
                    "plat": pid, "plat_name": pname,
                    "ident": "discovery-candidate", "free_from": None,
                    "access_modes": c.get("access_modes") or [],
                })

    # ── ニコニコ漫画: work-level update dates ──────────────────────────────────────────────────
    # The platform states that a work updated on a date, and never which chapter. So these attest
    # the update and nothing about its contents — no chapter title, no number, and therefore
    # `unclassified` as a type, the same shape a comparator claim has but with the platform itself
    # as the source rather than a listing site.
    nf = pathlib.Path("data/source/nicovideo/nicovideo.yaml")
    if nf.exists():
        d = yaml.safe_load(nf.read_text()) or {}
        for w in d.get("works") or []:
            u = str(w.get("updated") or "")[:10]
            if not u or u < wcut or u > wtoday:
                continue
            # "[ N話 無料 ]" means N episodes are free, not that the newest one is. Claiming the
            # update is free on that basis would put paywalled chapters in the free view, so it is
            # only claimed when every episode is free.
            eps, free_eps = w.get("episode_count"), w.get("free_episodes")
            all_free = bool(eps and free_eps and free_eps >= eps)
            started = str(w.get("started") or "")[:10]
            releases.append({
                "id": f"nicovideo:{w.get('comic_id')}:{u}", "work": w.get("work_title"),
                "ep": "", "type": "unclassified", "adv": True, "web": "serialised",
                "pub": u, "seen": str(d.get("retrieved", "")),
                "basis": "observed", "conf": "reported",
                "why": "work-level update date stated by the platform; chapter not identified",
                "moved": "", "url": w.get("url"), "author": w.get("author", ""),
                "plat": "nicovideo", "plat_name": "ニコニコ漫画",
                "ident": "discovery-candidate", "free_from": None,
                "access_modes": ["free"] if all_free else [],
                "episode_count": eps, "free_episodes": free_eps,
                "started": started or None,
                "work_level": True,
            })

    # Platform-wide access defaults, applied only where the source gave no per-chapter value.
    default_access = {}
    for pl in (yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text()) or {}).get("platforms") or []:
        if pl.get("default_access"):
            default_access[pl["name"]] = (pl["default_access"], pl.get("default_access_basis", ""))

    for r in releases:
        r["provenance"] = "attested"
        if not r.get("access_modes"):
            da = default_access.get(r.get("plat_name") or "")
            if da:
                r["access_modes"] = [da[0]]
                r["access_basis"] = da[1]
        # Free view membership. `free-timed` counts: rate-limited free (待てば無料, one chapter a
        # day per series with an account) is still free to a reader willing to wait.
        am = r.get("access_modes") or []
        # One category, not two. A chapter that has just come out from behind a paywall and a
        # chapter that was always free are the same thing to a reader asking "what is the newest
        # I can read for free" — which is the question this view answers. `became_free` is still
        # recorded, but it is a reason, not a separate kind of update.
        r["free"] = bool(r.get("free_from")) or bool(r.get("became_free")) \
            or any(m in ("free", "free-timed") for m in am)

        # Chapters the reader could pay for right now, ahead of the free line. Attached to every
        # row for the work so the interface can lead with it: "the newest free chapter is X, and
        # there are N paid ones past it" is more useful than either fact alone.
        ah = fuz_ahead.get(norm_work(r.get("work") or "")) if r.get("plat") == "comic-fuz" else None
        if ah:
            r["ahead_n"] = ah["n"]
            r["ahead_ep"] = ah["newest_ep"]
            r["ahead_next_free"] = ah["free_from"]
            r["ahead_next_ep"] = ah["ep"]

    # ── provisional claims from the comparator sites (§5) ──────────────────────────────────────
    # Taken as provisionally true for one question only: that a work updated, and roughly when.
    # A claim is a FLOOR, not an addition — where a platform attests the same work on the same
    # date, the attested record wins and the claim is dropped.
    # Built from the SOURCE layer, not from the windowed feed. The platform windows are 21 days
    # and the comparator claim window is 60, so a claim older than 21 days could never be
    # superseded by the attested chapter it duplicates — ぷれいめ～と showed 要確認 on a date we
    # hold カドコミ's own chapter for. A claim is a floor, and the floor applies whether or not the
    # attested release happens to fall inside the feed window (§5).
    attested_keys = {(norm_work(r["work"]), r["pub"]) for r in releases}
    for f in (glob.glob("data/source/kadokomi/chapters.yaml")
              + glob.glob("data/source/comicfuz/works.yaml")
              + glob.glob("data/source/webpages/*.yaml")):
        d0 = yaml.safe_load(open(f)) or {}
        for w in d0.get("works") or []:
            ti = norm_work(w.get("work_title") or w.get("title") or "")
            if not ti:
                continue
            for c in w.get("chapters") or []:
                u = str(c.get("updated") or "")[:10]
                if u:
                    attested_keys.add((ti, u))
    claim_index = {}
    # Canonicalise platform names through the registry's aliases, so a site the comparators label
    # two ways (ニコニコ静画 / ニコニコ漫画) reads as one platform and dedupes as one.
    alias_to_name, channels = {}, {}
    for pl in (yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text()) or {}).get("platforms") or []:
        for al in (pl.get("aliases") or []) + [pl.get("name")]:
            if al:
                alias_to_name[norm_work(al)] = pl.get("name")
        # Some names the comparators use are CHANNELS on another platform rather than platforms —
        # きららベース is an official channel on ニコニコ漫画 carrying 芳文社 titles. Presenting one
        # as a platform implies the work is published there, when it is a syndicated appearance.
        if pl.get("channel_of"):
            channels[norm_work(pl["name"])] = {
                "name": pl["name"], "host": pl["channel_of"],
                "syndicated": bool(pl.get("syndicated")),
                "origin": pl.get("origin_publisher"), "home": pl.get("likely_home"),
            }
    attested_works = {norm_work(r["work"]) for r in releases}
    # 百合ナビ runs title and author together in one cell ("ばっどがーる 肉丸"), so a claim from it
    # displays the pair as if it were a title. Where the cell begins with a title we hold from an
    # attesting source, split it; the remainder is the author. Where it does not, the cell is left
    # whole and flagged, because guessing the boundary would invent a title.
    known_titles = {}
    for src in ("data/source/kadokomi/catalogue.yaml", "data/source/kadokomi/chapters.yaml",
                "data/source/comicfuz/works.yaml", "data/source/comicfuz/resolved.yaml"):
        f = pathlib.Path(src)
        if not f.exists():
            continue
        for w in (yaml.safe_load(f.read_text()) or {}).get("works") or []:
            ti = w.get("title") or w.get("work_title")
            if ti:
                known_titles[norm_work(ti)] = ti
    for f in glob.glob("data/source/webpages/*.yaml") + glob.glob("data/source/gigaviewer/*-series.yaml"):
        d0 = yaml.safe_load(open(f)) or {}
        for w in (d0.get("works") or []) + (d0.get("series") or []):
            ti = w.get("work_title") or w.get("title")
            if ti:
                known_titles[norm_work(ti)] = ti
    for r in releases:
        known_titles.setdefault(norm_work(r["work"]), r["work"])
    # Web漫画アンテナ lists a clean title in its own cell. It is not an attesting source, but a
    # title string is all that is needed to locate the boundary in a 百合ナビ cell — the split is
    # then checked against the cell itself, so a wrong title simply fails to match.
    _cf = pathlib.Path("data/source/comparators/claims.yaml")
    if _cf.exists():
        for c in (yaml.safe_load(_cf.read_text()) or {}).get("updates") or []:
            if not c.get("raw_cell") and c.get("work"):
                known_titles.setdefault(norm_work(c["work"]), c["work"])

    def split_cell(cell):
        n = norm_work(cell)
        best = None
        for k, ti in known_titles.items():
            if len(k) >= 2 and n.startswith(k) and (best is None or len(k) > len(best[0])):
                best = (k, ti)
        if not best:
            return cell, None, False
        # Recover the author by length: the normalised prefix maps back to a raw prefix.
        raw = cell.strip()
        for cut in range(len(raw), 0, -1):
            if norm_work(raw[:cut]) == best[0]:
                return best[1], raw[cut:].strip(" 　/・") or None, True
        return best[1], None, True

    # Titles the comparators list in a work position that are not works — a magazine's own channel
    # page updates whenever anything on it updates, and reads as a work. See platforms.yaml.
    not_works = {norm_work(x["title"]) for x in
                 (yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text()) or {}).get("not_works") or []}

    cf = pathlib.Path("data/source/comparators/claims.yaml")
    claims_kept, phantom = 0, 0
    if cf.exists():
        d = yaml.safe_load(cf.read_text()) or {}
        for c in d.get("updates") or []:
            w, when = c.get("work"), str(c.get("date") or "")
            if not w or not when:
                continue
            author = None
            unsplit = False
            if c.get("raw_cell"):
                w, author, ok = split_cell(w)
                unsplit = not ok
            nw = norm_work(w)
            if nw in not_works:
                phantom += 1
                continue
            if (nw, when) in attested_keys:
                continue
            # 百合ナビ runs title and author together in one cell, so an exact-key test misses a
            # claim that duplicates an attested release — "リリィズコンプレックス 館山けーた" against
            # "リリィズコンプレックス". Suppress a claim whose cell starts with a title we already
            # attest on that date.
            if any(nw.startswith(k) for k, kd in attested_keys if kd == when and len(k) >= 2):
                continue
            # The two comparators overlap, and 百合ナビ's cell carries the author, so the same
            # update arrives twice under different strings. Keep the first and record that both
            # reported it, rather than showing the reader one event twice.
            dup = next((c2 for c2 in claim_index.get(when, [])
                        if nw.startswith(c2["nw"]) or c2["nw"].startswith(nw)), None)
            if dup:
                srcs = set(dup["rel"].get("claim_source", "").split("+")) | {c.get("source")}
                dup["rel"]["claim_source"] = "+".join(sorted(s for s in srcs if s))
                continue
            # A claim for a work we already attest elsewhere on another date is still useful:
            # it records an update we did not see. Kept, but flagged.
            releases.append({
                "id": f"claim:{c.get('source')}:{nw}:{when}", "work": w, "ep": "",
                "type": "unclassified", "adv": True, "web": "serialised", "pub": when,
                "seen": str(d.get("retrieved", "")), "basis": "claimed", "conf": "reported",
                "why": "", "moved": "", "url": c.get("url"), "author": author or "",
                "title_unsplit": unsplit,
                "plat": "claim",
                "plat_name": alias_to_name.get(norm_work(c.get("platform") or ""),
                                               c.get("platform") or "?"),
                "channel": channels.get(norm_work(c.get("platform") or "")),
                "ident": "comparator-claim", "free_from": None, "access_modes": [],
                "provenance": "claimed", "claim_source": c.get("source"),
                "also_attested_elsewhere": nw in attested_works,
            })
            claim_index.setdefault(when, []).append({"nw": nw, "rel": releases[-1]})
            claims_kept += 1

    # A channel is a section of a host platform, not a platform. Naming the host is always correct.
    # Calling a particular work *syndicated*, though, is a claim about where it was first published,
    # and that is per-work: きららベース carries 芳文社 titles from COMIC FUZ, but 魔女まじょS-WITCH
    # is native to the channel and returns nothing on comic-fuz.com. So 転載 is asserted only where
    # the work is confirmed on the origin platform; otherwise the origin is recorded as unknown.
    fuz_confirmed = set()
    _rf = pathlib.Path("data/source/comicfuz/resolved.yaml")
    if _rf.exists():
        for w in (yaml.safe_load(_rf.read_text()) or {}).get("works") or []:
            fuz_confirmed.add(norm_work(w["title"]))
    for f in glob.glob("data/source/comicfuz/*.yaml"):
        for w in (yaml.safe_load(open(f)) or {}).get("works") or []:
            t = w.get("work_title") or w.get("title")
            if t:
                fuz_confirmed.add(norm_work(t))

    for r in releases:
        ch = r.get("channel")
        if ch:
            r["plat_name"] = f"{ch['host']}（{ch['name']}）"
            elsewhere = norm_work(r["work"]) in fuz_confirmed
            r["syndicated"] = bool(ch["syndicated"] and elsewhere)
            if r["syndicated"]:
                r["origin_note"] = (f"syndicated on {ch['host']}; confirmed on {ch['origin']}'s "
                                    f"own platform, which is where it originates")
            else:
                r["origin_note"] = (f"carried on {ch['host']} in the {ch['name']} channel, which is "
                                    f"a section of that site rather than a platform. Whether it was "
                                    f"first published here or elsewhere is not established.")
                r["origin_unknown"] = True

    # ── update kind: new series / new chapter / other ──────────────────────────────────────────
    # Derived from positive evidence only. An earlier version inferred `new-series` from "first
    # appearance in our data", which in a three-week window is true of almost everything and
    # asserted far more than we know — a long-running work seen for the first time is not new.
    #
    # So: a numbered first chapter is evidence of a new series; a later-numbered chapter of an
    # ongoing one; notices and trials are neither. A comparator claim carries no episode
    # information at all, so it stays `unknown` rather than being guessed into a category.
    OTHER_TYPES = {"notice", "apology-art", "trial", "republication"}

    # An earlier release for the same work PROVES this is not the start of it. That is a stronger
    # and safer signal than reading the title, and it rescues works whose chapters are named rather
    # than numbered — スズラン手帖's anthology entries, for instance.
    attested_titles = {norm_work(r["work"]) for r in releases if r.get("provenance") == "attested"}
    earliest, latest, count = {}, {}, {}
    for r in sorted(releases, key=lambda r: r["pub"]):
        nw = norm_work(r["work"])
        earliest.setdefault(nw, r["pub"])
        latest[nw] = r["pub"]
        count[nw] = count.get(nw, 0) + 1

    # Works the sources mark as finished. GigaViewer carries 完結 as a genre, カドコミ states a
    # serialisation status, and Web漫画アンテナ tags its listings. None of these says which chapter
    # was the last, only that the series has ended — enough to corroborate, not to assert alone.
    completed = {}
    for f in glob.glob("data/source/gigaviewer/*-series.yaml") + glob.glob("data/source/webpages/*.yaml"):
        d0 = yaml.safe_load(open(f)) or {}
        for w in (d0.get("series") or []) + (d0.get("works") or []):
            t = w.get("title") or w.get("work_title")
            if t and ("完結" in (w.get("genres") or []) or w.get("status") in ("完結", "finished")):
                completed[norm_work(t)] = True
    kf = pathlib.Path("data/source/kadokomi/chapters.yaml")
    if kf.exists():
        for w in (yaml.safe_load(kf.read_text()) or {}).get("works") or []:
            if w.get("status") == "finished" and w.get("work_title"):
                completed[norm_work(w["work_title"])] = True
    cf2 = pathlib.Path("data/source/comparators/claims.yaml")
    if cf2.exists():
        for c in (yaml.safe_load(cf2.read_text()) or {}).get("updates") or []:
            if "完結" in (c.get("listing_tags") or []) and c.get("work"):
                completed[norm_work(c["work"])] = True

    # An entry is judged against its own series' naming, not against a keyword list. A title
    # carrying 巻 among sixty that do not is a volume announcement — うさぎはかく語りき files
    # 3巻発売フェア and 第2巻 書店フェア among its chapters. But some series genuinely count in
    # volumes, and a keyword rule would mistype every one of their instalments. So the test is the
    # proportion: rare in this series means it is not how this series names its chapters.
    #
    # The denominator comes from the full source history, not the feed window, or a series with two
    # chapters in view and one of them promotional would read as 50% and escape.
    VOLUME_OUTLIER_MAX = 0.30
    MIN_SIBLINGS = 4
    series_titles = defaultdict(list)
    for f in (glob.glob("data/source/kadokomi/chapters.yaml")
              + glob.glob("data/source/comicfuz/works.yaml")
              + glob.glob("data/source/webpages/*.yaml")
              + glob.glob("data/source/gigaviewer/*.yaml")):
        d0 = yaml.safe_load(open(f)) or {}
        for w in d0.get("works") or []:
            ti = norm_work(w.get("work_title") or w.get("title") or "")
            if ti:
                series_titles[ti] += [c.get("title") or "" for c in w.get("chapters") or []]
    for r in releases:
        series_titles.setdefault(norm_work(r["work"]), []).append(r.get("ep") or "")

    for r in releases:
        ep = r.get("ep") or ""
        if r["type"] in OTHER_TYPES or NON_STORY_RE.search(ep) or ep.strip() == "イラスト":
            r["kind"], r["kind_basis"] = "other", "notice, artwork, trial or announcement"
            continue
        sibs = series_titles.get(norm_work(r["work"])) or []
        if VOLUME_MARK_RE.search(ep) and len(sibs) >= MIN_SIBLINGS:
            marked = sum(1 for s in sibs if VOLUME_MARK_RE.search(s))
            share = marked / len(sibs)
            if share <= VOLUME_OUTLIER_MAX:
                r["kind"] = "other"
                r["kind_basis"] = (f"reads as a volume, artwork or notice, and only {marked} of "
                                   f"{len(sibs)} chapters in this series do ({share:.0%}) — not "
                                   f"how this series names its instalments")
                r["kind_inferred"] = True
                continue
        if r["type"] == "extra" or EXTRA_RE.search(ep):
            r["kind"], r["kind_basis"] = "new-chapter", "extra or side story — content, not notice"
            continue
        n = ep_number(ep)
        has_earlier = earliest.get(norm_work(r["work"]), r["pub"]) < r["pub"]
        # Checked before the numbering, because a finale is usually numbered too (第30話 最終回) and
        # the ending is the more informative fact about it.
        if FINAL_RE.search(unicodedata.normalize("NFKC", ep)):
            r["kind"], r["kind_basis"] = "final", "title states this is the last chapter"
        elif completed.get(norm_work(r["work"])) and r["pub"] == latest.get(norm_work(r["work"])):
            # The platform marks the series 完結 and this is the newest release we hold for it.
            # Weaker than the title saying so — the tag may have been applied after the fact — so
            # it is flagged as inferred and the interface marks it.
            r["kind"], r["kind_basis"] = "final", "series marked 完結; newest release we hold"
            # Distinct from the blanket `kind_inferred` set at the end of this loop, which is true
            # of every kind. This marks the weaker of the two routes to `final` specifically.
            r["final_inferred"] = True
        elif r.get("started") and r["started"] == r["pub"]:
            # The platform states the serialisation start date and it is this update. Positive
            # evidence, unlike "first time we saw it".
            r["kind"], r["kind_basis"] = "new-series", "platform states the serialisation started"
        elif n == 1:
            r["kind"], r["kind_basis"] = "new-series", "episode numbered 1"
        elif n is not None:
            r["kind"], r["kind_basis"] = "new-chapter", f"episode numbered {n}"
        elif has_earlier:
            # Not the first release we hold for this work, so not the start of it.
            r["kind"], r["kind_basis"] = "new-chapter", "work has an earlier release here"
        elif attested_titles and any(
                norm_work(r["work"]).startswith(a) or a.startswith(norm_work(r["work"]))
                for a in attested_titles if len(a) > 2):
            # A claim naming a work we attest elsewhere: the work demonstrably has chapters here,
            # so an update to it is a further one rather than a start.
            r["kind"] = "new-chapter"
            r["kind_basis"] = "work is attested elsewhere in this database"
        elif count.get(norm_work(r["work"]), 0) > 1:
            # Several unnumbered entries for one work, all bearing the same date — a back catalogue
            # arriving at once, as with an anthology. They are chapters of a series rather than a
            # series each. One of them is genuinely its first, and we cannot tell which, so the
            # basis says so rather than the label implying certainty.
            r["kind"] = "new-chapter"
            r["kind_basis"] = "one of several entries for this work; first not identifiable"
        elif r["type"] == "oneshot":
            r["kind"], r["kind_basis"] = "new-series", "one-shot"
        else:
            r["kind"] = "unknown"
            r["kind_basis"] = ("listing site names no chapter, and the work is not tracked on a "
                               "platform we reach" if r.get("provenance") == "claimed"
                               else "no chapter number and no earlier release held")
        # Inference from what we hold, never a statement by the publisher.
        r["kind_inferred"] = True

    # Reading-quality ranking is editorial curation, kept out of the source layer (§5).
    ranks, plat_meta = {}, {}
    pf = pathlib.Path("data/platforms.yaml")
    if pf.exists():
        for pl in (yaml.safe_load(pf.read_text()) or {}).get("platforms") or []:
            ranks[pl["name"]] = pl.get("reading_rank")
            plat_meta[pl["name"]] = {"rank": pl.get("reading_rank"),
                                     "overlap": pl.get("overlap")}

    # Merge the same chapter seen on several platforms, and point at the best source carrying it.
    merged = merge_releases(
        [{"work": r["work"], "episode": r["ep"], "platform": r["plat_name"] or r["plat"],
          "date": r["pub"], "url": r["url"], "_r": r} for r in releases], ranks)
    by_key = {(m["work"], m["episode"]): m for m in merged}
    for r in releases:
        m = by_key.get((r["work"], r["ep"]))
        if m:
            r["preferred"] = m["preferred"]
            r["also_on"] = m["also_on"]
            r["is_preferred"] = (r["plat_name"] or r["plat"]) == m["preferred"]
        else:
            r["is_preferred"] = True
    # Only the preferred source of each chapter is shown; alternatives ride along on that entry.
    # 試し読み-only series are not web publication (DEFINITIONS §6), so they are dropped from the
    # feed outright rather than hidden behind a filter — a hidden entry still inflates totals and
    # the acceptance measure. They remain as print candidates, which is what they actually are.
    samples = [r for r in releases if r.get("web") == "promotional-sample-only"]
    releases = [r for r in releases if r.get("web") != "promotional-sample-only"]
    releases = [r for r in releases if r.get("is_preferred")]
    releases.sort(key=lambda r: r["pub"], reverse=True)

    lapsed = [c for c in carriage(
        [{"work": r["work"], "episode": r["ep"], "platform": r["plat_name"] or r["plat"]}
         for r in releases]) if c["status"] == "lapsed"]

    # Web works confirmed against a publisher after discovery named them. These have no MADB
    # record — they are web-native and mostly too recent for the print sources — so they compile
    # separately rather than being forced through the tankōbon work-merge. Folding them into the
    # main work table is a schema step, not a formatting one, and is deliberately not rushed here.
    web_works = []
    for f in sorted(glob.glob("data/source/kadokomi/confirmed.yaml")):
        d = yaml.safe_load(open(f)) or {}
        for w in d.get("works") or []:
            if not w.get("marketing_label") and not w.get("content_tier"):
                errors.append(f"{w.get('work_title')}: confirmed web work with neither axis set")
            if w.get("marketing_label") and not w.get("marketing_label_basis"):
                errors.append(f"{w.get('work_title')}: marketing_label without basis (DEFINITIONS §5)")
            web_works.append({
                "title": w.get("work_title"), "url": w.get("url"),
                "platform": d.get("source"), "status": w.get("serialization_status"),
                "tags": w.get("tags", []), "label": w.get("label"),
                "authors": w.get("authors", []),
                "marketing_label": w.get("marketing_label"),
                "marketing_label_basis": w.get("marketing_label_basis"),
                "content_tier": w.get("content_tier"),
                "discovered_via": w.get("discovered_via"),
                "oneshot": w.get("is_oneshot"),
            })

    # Print works reached through a web sample: catalogue candidates, not releases.
    print_candidates = []
    for f in sorted(glob.glob("data/source/gigaviewer/*-print-candidates.yaml")):
        d = yaml.safe_load(open(f)) or {}
        for c in d.get("candidates") or []:
            print_candidates.append({**{k: c.get(k) for k in
                ("work_title", "author", "sample_count", "sample_url", "label", "status")},
                "platform": d.get("platform")})

    # Discovery candidates are NOT records and are kept in a separate structure so nothing
    # downstream can mistake them for attested data (§1).
    queue = []
    for f in sorted(glob.glob("data/queue/*.yaml")):
        d = yaml.safe_load(open(f)) or {}
        for c in d.get("candidates") or []:
            queue.append({"work": c.get("work_title"), "signal": c.get("signal"),
                          "url": c.get("url"), "headline": c.get("headline"),
                          "announced": str(c.get("announced", "")),
                          "source": d.get("source"), "status": c.get("status")})

    (out / "feed.json").write_text(json.dumps(
        {"releases": releases, "platforms": platforms, "queue": queue,
         "print_candidates": print_candidates, "web_works": web_works,
         "samples_dropped": len(samples),
         "platform_meta": plat_meta, "lapsed": lapsed},
        ensure_ascii=False, indent=1, default=jsonable))

    from collections import Counter as _C
    print(f"syndicated      : {sum(1 for r in releases if r.get('syndicated'))}")
    print(f"provenance      : {dict(_C(r.get('provenance') for r in releases))}")
    print(f"update kind     : {dict(_C(r.get('kind') for r in releases))}")
    print(f"free view       : {sum(1 for r in releases if r.get('free'))} of {len(releases)}")
    print(f"samples dropped : {len(samples)} (promotional 試し読み — kept as print candidates)")
    print(f"identification  : {dict(_C(r.get('ident') for r in releases))}")
    am = _C(m for r in releases for m in (r.get("access_modes") or []))
    if am:
        print(f"access modes    : {dict(am)}")
    if lapsed:
        print(f"carriage lapses : {len(lapsed)}")
    serialised = sum(1 for r in releases if r.get("web") == "serialised")
    print(f"releases        : {len(releases)} from {len(platforms)} platform(s) "
          f"({serialised} serialised, {len(releases)-serialised} promotional samples)")
    print(f"print candidates: {len(print_candidates)} from web samples")
    wl = sum(1 for w in web_works if w.get("marketing_label") == "yuri")
    print(f"web works       : {len(web_works)} confirmed ({wl} with a publisher yuri label)")
    print(f"queue           : {len(queue)} unconfirmed candidates")
    print(f"works compiled  : {len(works)}")
    print(f"volumes         : {sum(w['volume_count'] for w in works)}")
    print(f"with openBD     : {sum(1 for w in works if 'openbd' in w['sources'])}")
    print(f"unclassified    : {len(warnings)} works have no content_tier (needs human review)")
    print(f"written         : {out}/works.json, {out}/index.json")


if __name__ == "__main__":
    main()
