#!/usr/bin/env python3
"""Merge source layers, validate, and compile the published dataset.

Source records (data/source/<source>/) are stored as fetched and never edited. Curation lives in
data/overlay/ and always wins. This step merges them by source priority, enforces the validation
rules in REQUIREMENTS §6, and writes data/build/.

Fails closed: any validation error aborts the build without writing.

Usage:  build.py [--out data/build]
"""
import argparse, datetime, glob, json, pathlib, re, sys, unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, "adapters")
from crossplatform import carriage, episode_key, merge_releases  # noqa: E402

import yaml

# REQUIREMENTS §1. A field whose provenance is not here fails the build.
# Tier A/B attesting sources only. Discovery-only sources (Tier C/D) never appear here — they feed
# data/queue/, which is deliberately outside the source tree so nothing can promote a candidate
# into a record by accident.
ALLOWED_SOURCES = {"madb", "openbd", "ndl", "openbd-jpro", "publisher", "ichijinsha",
                   "gigaviewer", "kadokomi", "comicfuz", "webpages", "comparators", "nicovideo",
                   "pixivcomic", "reachable"}

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
# Several publishers say so in the title rather than anywhere structured: 【読切】吸血少女と…,
# 【コミックDAYS読み切り】私のヒーロー, 読み切り作品, and 魔法使いの作庭/よみきり which puts it in
# the WORK title. Confirmation establishes is_oneshot properly but only reaches works we discovered
# through editorial coverage; this catches the rest, which were arriving as 新話.
ONESHOT_RE = re.compile(r"読切|読み切り|よみきり")
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


JST = datetime.timezone(datetime.timedelta(hours=9))


def jst_date(stamp):
    """The date a Japanese platform considers a timestamp to fall on.

    Atom <updated> is UTC. 少年ジャンプ+ and サンデーうぇぶり publish at 15:00Z, which is midnight JST
    the NEXT day, so taking the first ten characters dated every one of their chapters a day early:
    春雷卓球's page prints 2026年07月31日 against a stamp of 2026-07-30T15:00:00Z, and the series
    updates 毎週金曜 — the 31st is the Friday.

    コミックDAYS stamps 03:00Z and 一迅プラス 02:00Z, both mid-morning JST and unaffected, which is why
    this survived: it is invisible on whichever platform one happens to check first.

    A bare date passes through unchanged; only a real timestamp is converted.
    """
    s = str(stamp or "").strip()
    if len(s) <= 10 or "T" not in s:
        return s[:10]
    try:
        d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s[:10]
    return d.astimezone(JST).date().isoformat() if d.tzinfo else s[:10]


def norm_work(s):
    """Normalise a work title for comparison.

    NFKC first. Without it （私に） and (私に) compare unequal, as do ２ and 2, and ！ and !.
    That duplicated series in the feed. The comparators and the platforms render all of these
    inconsistently, so folding them is the only way titles match across sources.

    The long vowel mark ー is deliberately NOT stripped: it is a letter in katakana, not
    punctuation, and removing it would merge genuinely different titles.

    Nor is '+', for the same reason and a sharper one: it marks a SEQUEL. citrus and citrus+ are
    two works with two URLs on 一迅プラス, and stripping it merged them into one everywhere in the
    database — the sequel's releases filed under the original. NFKC has already folded ＋ to +, so
    keeping it costs no cross-source matching.
    """
    s = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", s or "")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"""[\s\-.=、。･・!?,:;'"“”‘’()\[\]{}「」『』【】〈〉《》〔〕~〜_/\\|*&#@]""",
                  "", s.strip().lower())


def load_dir(p):
    return [yaml.safe_load(open(f)) for f in sorted(glob.glob(f"{p}/*.yaml"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/build")
    a = ap.parse_args()

    # pixivコミック has two possible sources — the rendered pages and adapters/pixivcomic/ — and
    # they carry the same chapters. The dedup keys on (work, episode, platform) and would collapse
    # the duplication silently rather than reporting it, so the overlap is caught here instead.
    _px_new = glob.glob("data/source/pixivcomic/*.yaml")
    _px_old = pathlib.Path("data/source/webpages/rendered-pixivcomic.yaml")
    if _px_new and _px_old.exists():
        sys.exit(f"VALIDATION: pixivコミック is present twice — {_px_old} and "
                 f"{', '.join(_px_new)}. The adapter replaces the rendered output; delete the "
                 "rendered file once its chapters have been compared against the new source.")

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
        # Per-series Atom feeds carry works-with-chapters rather than a flat release list, the same
        # shape the webpages adapters emit. Read below with those, not here (§5).
        if d.get("record_type") == "web_work_chapters":
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
                "pub": jst_date(r.get("date") or r.get("platform_updated", "")),
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
    # Facts about chapters too old to be releases, kept so they can still be carried onto the rows
    # that are in the feed. Keyed (work, platform, chapter).
    field_facts = {}
    wcut = str(datetime.date.today() - datetime.timedelta(days=WEBPAGE_FEED_DAYS))
    wtoday = str(datetime.date.today())
    # カドコミ: same shape as the webpages adapters, but it does apply a 百合 tag, so its works
    # carry a marketing_label where present.
    # Works the platform itself calls a one-shot. Confirmation records is_oneshot and the release
    # loop typed everything `chapter` regardless, so a one-shot arrived in the feed as an ordinary
    # instalment of a series with one instalment.
    oneshot_works = set()
    _cf = pathlib.Path("data/source/kadokomi/confirmed.yaml")
    if _cf.exists():
        for w in (yaml.safe_load(_cf.read_text()) or {}).get("works") or []:
            if w.get("is_oneshot") and w.get("work_title"):
                oneshot_works.add(norm_work(w["work_title"]))

    kf = pathlib.Path("data/source/kadokomi/chapters.yaml")
    if kf.exists():
        d = yaml.safe_load(kf.read_text()) or {}
        for w in d.get("works") or []:
            for c in w.get("chapters") or []:
                u = str(c.get("updated") or "")
                if not u or u < wcut or u > wtoday:
                    continue
                releases.append({
                    "type_override": ("oneshot" if norm_work(w.get("work_title") or "")
                                      in oneshot_works else None),
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

    for f in (sorted(glob.glob("data/source/webpages/*.yaml"))
              + sorted(glob.glob("data/source/gigaviewer/*-series-feeds.yaml"))
              + sorted(glob.glob("data/source/gigaviewer/*-confirmed.yaml"))
              + sorted(glob.glob("data/source/pixivcomic/*.yaml"))):
        d = yaml.safe_load(open(f)) or {}
        pid, pname = d.get("platform"), d.get("platform_name")
        for w in d.get("works") or []:
            # A file that gathers works from several platforms states the platform per work; the
            # file-level name is empty there, and reading only that left 54 rows labelled "?".
            pname_w = w.get("platform_name") or pname
            pid_w = w.get("platform") or pid
            # A work reached through editorial coverage was published before we heard of it —
            # 百合ナビ covers one-shots weeks late, and a one-shot is gone from every listing by
            # then. Dropping it for being older than the window means it can never appear at all,
            # however often we poll: polling frequency cannot retrieve something that was already
            # old when we first learned it existed. So confirmation-sourced works are admitted on
            # the date we learned of them, carrying their true publication date with them.
            late = bool(w.get("discovered_via"))
            # Some statements are made about the work rather than about a chapter. フラコミlike!
            # writes its whole access policy into the page title — 銀の河に星の城 | いつでも無料 |
            # フラコミlike! | 空木帆子 — so there is an author and an access state and no chapter
            # list to hang them on. Recorded against the work, with an empty chapter key.
            if not (w.get("chapters") or []) and (w.get("author") or w.get("access_modes")):
                field_facts[(norm_work(w.get("work_title") or ""), pname_w, "")] = {
                    "author": w.get("author"), "access_modes": w.get("access_modes")}
            for c in w.get("chapters") or []:
                u = str(c.get("updated") or "")
                if not u or u > wtoday:
                    continue
                if u < wcut and not late:
                    # Out of the window, so not a release — but still a fact about a chapter, and
                    # the row-level backfill goes out precisely to fetch facts about chapters that
                    # are old. Its reading of 吸血少女とウンディーネ (published 80 days ago, still in
                    # the feed as a late discovery) was being discarded here, before anything could
                    # carry the access state onto the row that needed it. Keep the fact, drop the
                    # release.
                    if c.get("author") or c.get("access_modes") or w.get("author"):
                        field_facts[(norm_work(w.get("work_title") or ""), pname_w,
                                     norm_work(c.get("title") or ""))] = {
                            "author": c.get("author") or w.get("author"),
                            "access_modes": c.get("access_modes")}
                    continue
                releases.append({
                    "late_discovered": u < wcut,
                    "discovered_on": str(d.get("retrieved", "")) if u < wcut else None,
                    "id": f"{pid}:{c.get('url') or c.get('title')}", "work": w.get("work_title"),
                    # The platform's own count decides this: a series with one episode is a
                    # one-shot. Confirmation established it and the loop was discarding it.
                    # Subtitle included, as it already is for the gigaviewer sources. pixivコミック
                    # numbers some works plainly — its numbering_title is "1", "2", "3" — and puts
                    # the chapter's actual name in sub_title. Dropping it left 壊していいよ、すいか
                    # ちゃん showing four chapters called 1, 2, 3 and 4, where the platform shows
                    # 1 かくして二人は出会った. The field was populated, so nothing flagged it.
                    "ep": (c.get("title") or "")
                          + (f" {c['subtitle']}" if c.get("subtitle") else ""),
                    "type": "oneshot" if w.get("is_oneshot") else "chapter", "adv": True,
                    "web": "serialised", "pub": u, "seen": str(d.get("retrieved", "")),
                    # A heuristically-parsed date is not the same kind of fact as one a platform
                    # states, and saying so is the whole price of the generic extractor. Carried
                    # through to the feed rather than left in the source layer.
                    "basis": c.get("date_basis") or d.get("date_basis") or "bootstrap",
                    "conf": d.get("date_confidence") or "reported",
                    "why": ("date matched as a pattern in the page, not stated by the platform"
                            if (c.get("date_basis") or d.get("date_basis")) == "heuristic" else ""),
                    "moved": "",
                    "url": c.get("url") or w.get("url"),
                    # Author may be stated per chapter (GigaViewer feeds) or per work; both were
                    # being dropped in favour of an empty string.
                    "author": c.get("author") or w.get("author") or "",
                    "plat": pid_w, "plat_name": pname_w,
                    "ident": "discovery-candidate",
                    "free_from": c.get("free_from"),
                    "access_modes": c.get("access_modes") or [],
                })

    for r in releases:
        if r.pop("type_override", None):
            r["type"] = "oneshot"

    # A platform feed types an entry `unclassified` when its own heuristic cannot tell what it is.
    # Where we HAVE told — a chapter number parsed out of the title — the label should follow:
    # 雨夜の月's 第５０−２話　夢現 was showing as 新話 and 未分類 at the same time, which is the
    # interface disagreeing with itself in front of the reader.
    for r in releases:
        if r.get("type") == "unclassified" and ep_number(r.get("ep") or "") is not None:
            r["type"] = "chapter"
            r["type_basis"] = "numbered chapter, though the platform feed did not say so"

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
                # The newest episode named on the work page is the one the 更新 date refers to.
                "ep": w.get("latest_episode") or "",
                "type": "chapter" if w.get("latest_episode") else "unclassified",
                "adv": True, "web": "serialised",
                "pub": u, "seen": str(d.get("retrieved", "")),
                "basis": "observed", "conf": "reported",
                "why": "work-level update date stated by the platform; chapter not identified",
                "moved": "", "url": w.get("latest_episode_url") or w.get("url"),
                "author": w.get("author", ""),
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
    # The adapter registries carry aliases too, and only platforms.yaml was being read — so
    # 花とゆめ＋ (the antenna's full-width ＋) and 花とゆめ+ (the site's) stayed two platforms, and a
    # work carried once looked cross-published with itself.
    for _reg, _key in (("adapters/webpages/sites.yaml", "sites"),
                       ("adapters/gigaviewer/platforms.yaml", "platforms")):
        _f = pathlib.Path(_reg)
        if not _f.exists():
            continue
        for pl in (yaml.safe_load(_f.read_text()) or {}).get(_key) or []:
            for al in (pl.get("aliases") or []) + [pl.get("name")]:
                if al:
                    alias_to_name[norm_work(al)] = pl.get("name")
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
                "data/source/comicfuz/works.yaml", "data/source/comicfuz/resolved.yaml",
                "data/source/kadokomi/resolved.yaml", "data/source/nicovideo/resolved.yaml",
                "data/source/comparators/resolved-titles.yaml"):
        f = pathlib.Path(src)
        if not f.exists():
            continue
        for w in (yaml.safe_load(f.read_text()) or {}).get("works") or []:
            ti = w.get("title") or w.get("work_title")
            if ti:
                known_titles[norm_work(ti)] = ti
    for f in (glob.glob("data/source/webpages/*.yaml")
              + glob.glob("data/source/gigaviewer/*-series.yaml")
              + glob.glob("data/source/pixivcomic/*.yaml")):
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

    # Full chapter histories we hold, by (work, platform), for contradicting a comparator.
    #
    # The test is whether the platform publishes a HISTORY or a survival set, and most publish the
    # latter. pixivコミック expires chapters: 異種族女子に〇〇する話 lists 第1話, 第2話, 第3話 ending
    # 2021 — the permanently-free opening, with the middle gone — and a comparator saying it updated
    # in 2026 is entirely consistent with that. Mean chapters per work says the same across the
    # board: comicfuz 62.7, kadokomi 19.5, pixivcomic 4.7. カドコミ returns latestEpisodes plus
    # firstEpisodes by construction, which is a window with a hole in the middle by design.
    #
    # Absence of evidence is only evidence of absence where the list is known to be complete, so
    # the sources permitted here are only those that return whole histories. Everything else can
    # attest what it shows and must not be used to deny what it does not.
    platform_history = {}
    for f in (glob.glob("data/source/gigaviewer/*-series-feeds.yaml")
              + glob.glob("data/source/gigaviewer/*-confirmed.yaml")
              + glob.glob("data/source/comicfuz/works.yaml")):
        d0 = yaml.safe_load(open(f)) or {}
        pn = norm_work(d0.get("platform_name") or "")
        for w in d0.get("works") or []:
            ti = norm_work(w.get("work_title") or w.get("title") or "")
            ds = [str(c.get("updated"))[:10] for c in (w.get("chapters") or [])
                  if c.get("updated")]
            if ti and pn and ds:
                platform_history[(ti, pn)] = ds

    # Platforms that publish no per-chapter dates. A claim naming one of them is unconfirmable by
    # nature, not by neglect, and the interface should say which it is.
    dateless_platforms = {norm_work(x["name"]) for x in
                          (yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text()) or {})
                          .get("no_chapter_dates") or []}

    # Attested dates by (work, platform), for recognising a claim that reports what we already hold.
    platform_dates = {}
    for r in releases:
        if r.get("provenance") == "attested" or r.get("basis") not in (None, "claimed"):
            platform_dates.setdefault(
                (norm_work(r.get("work") or ""),
                 norm_work(r.get("plat_name") or r.get("plat") or "")), []).append(r["pub"])

    contradicted, contradicted_works = 0, []
    CLAIM_DATE_SLACK = 2   # days either side

    def near_dates(when):
        try:
            d0 = datetime.date.fromisoformat(when)
        except ValueError:
            return ()
        return tuple(str(d0 + datetime.timedelta(days=k))
                     for k in range(-CLAIM_DATE_SLACK, CLAIM_DATE_SLACK + 1) if k)

    cf = pathlib.Path("data/source/comparators/claims.yaml")
    claims_kept, phantom, claims_superseded_nearby = 0, 0, 0
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
            # Comparators and platforms disagree by a day or two routinely — a listing site records
            # when it noticed, the platform when it published, and timezones and crawl schedules do
            # the rest. 白き乙女の人狼 is attested on 竹コミ for 2026-07-10 and claimed for 07-12.
            # Treating those as two events shows the reader one update twice, the second time
            # marked unconfirmed. Exact-date matching was too strict for what these dates are.
            if any((nw, d) in attested_keys for d in near_dates(when)):
                claims_superseded_nearby += 1
                continue
            # Same work AND same platform is a stronger match than same work alone, so it carries a
            # wider window. A listing site reports when it notices; the platform's own record dates
            # the same chapter a few days earlier, and the observed gaps cluster at 3–8 days with a
            # clear break after. Showing both is showing one event twice, the second time as an
            # empty row marked unconfirmed.
            pn_claim = alias_to_name.get(norm_work(c.get("platform") or ""), c.get("platform") or "")
            same_plat = platform_dates.get((nw, norm_work(pn_claim))) or []
            if same_plat and min(abs((datetime.date.fromisoformat(when)
                                      - datetime.date.fromisoformat(x)).days)
                                 for x in same_plat) <= 7:
                claims_superseded_nearby += 1
                continue
            # 百合ナビ runs title and author together in one cell, so an exact-key test misses a
            # claim that duplicates an attested release — "リリィズコンプレックス 館山けーた" against
            # "リリィズコンプレックス". Suppress a claim whose cell starts with a title we already
            # attest on that date.
            if any(nw.startswith(k) for k, kd in attested_keys if kd == when and len(k) >= 2):
                continue
            # A claim for a work whose full chapter history we hold on that very platform, with no
            # chapter anywhere near the claimed date, is not an unconfirmed report — it is a
            # report the platform contradicts. 君のせいなんだから、責任とってよね。 is claimed for
            # 2026-07-23; 一迅プラス's own feed lists six chapters ending 2026-06-17, paid ones
            # included. Leaving that as 要確認 implies we might yet confirm it. We have looked.
            # Three chapters at minimum before contradicting anyone. A history of one is not a
            # history — 浪人なんてろくでもない! had a single chapter held and was being used to
            # declare the comparator wrong, which is a stronger claim than the evidence carries.
            # A large gap between the claim and the newest chapter we hold is the signature of a
            # partial listing, not of a work that stopped. Platforms expire chapters — pixivコミック
            # leaves the permanently-free opening and takes the middle away — and several
            # GigaViewer installs serve only what is currently free: となりのヤングジャンプ averages
            # 1.3 chapters per work against コミックDAYS's 26.3. Where we are this far behind, the
            # honest reading is that we cannot see the whole run, whatever the reason.
            CONTRADICTION_MAX_GAP = 120   # days
            plat_hist = platform_history.get((nw, norm_work(c.get("platform") or "")))
            if plat_hist and (datetime.date.fromisoformat(when)
                              - datetime.date.fromisoformat(max(plat_hist))).days > CONTRADICTION_MAX_GAP:
                plat_hist = None
            if plat_hist and len(plat_hist) >= 3 and not any(abs((datetime.date.fromisoformat(when)
                                          - datetime.date.fromisoformat(x)).days) <= 7
                                     for x in plat_hist):
                contradicted += 1
                contradicted_works.append({
                    "work": w, "platform": c.get("platform"), "claimed": when,
                    "platform_latest": max(plat_hist),
                    "chapters_held": len(plat_hist), "source": c.get("source")})
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
                "unconfirmable": norm_work(c.get("platform") or "") in dateless_platforms,
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
    # Chapters, not just a confirmed title. resolved.yaml records that a work of this name exists
    # on FUZ, which is not the same as knowing the copy on the channel is that work — ぬるめた has a
    # shorter, older run on ニコニコ漫画 and a newer one on FUZ, and we hold no FUZ chapters for it
    # at all (its /series/ URL 404s). A title in common is not a syndication.
    fuz_confirmed = set()
    for f in glob.glob("data/source/comicfuz/*.yaml"):
        for w in (yaml.safe_load(open(f)) or {}).get("works") or []:
            t = w.get("work_title") or w.get("title")
            if t and (w.get("chapters") or w.get("episodes")):
                fuz_confirmed.add(norm_work(t))

    # A work confirmed on another platform, appearing on a known syndicator, is a syndicated
    # appearance — 魔法少女201 is 集英社's, carried on 少年ジャンプ+ and ヤンジャン+, and also on
    # ニコニコ漫画. Marking it there as if it originated is wrong twice over: it misattributes the
    # work, and it points a reader at the worse copy.
    _pl = (yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text()) or {}).get("platforms") or []
    syndicators = {p["name"] for p in _pl if p.get("syndication") or p.get("id") == "nicovideo"}
    rank_of = {p["name"]: (p.get("reading_rank") or 99) for p in _pl}

    origin_of = {}
    _rt = pathlib.Path("data/source/comparators/resolved-titles.yaml")
    if _rt.exists():
        for w in (yaml.safe_load(_rt.read_text()) or {}).get("works") or []:
            if w.get("platform"):
                origin_of[norm_work(w["title"])] = w["platform"]
    # Anything we attest on a platform that is not a syndicator is an origin for this purpose,
    # whether or not a resolved-titles row happens to name it. ばっどがーる was confirmed on FUZ
    # and its chapters held, yet its ニコニコ copy still read as original because the rule only
    # consulted one file. Where several carry it, the best-ranked wins — that is the whole point
    # of reading_rank.
    for r in releases:
        pn = r.get("plat_name") or ""
        if r.get("provenance") != "attested" or pn in syndicators or not pn:
            continue
        k = norm_work(r.get("work") or "")
        cur = origin_of.get(k)
        if cur is None or rank_of.get(pn, 99) < rank_of.get(cur, 99):
            origin_of[k] = pn
    # Syndication needs evidence that it is the SAME RUN, not just the same title. ぬるめた exists
    # twice: a shorter, older version on ニコニコ漫画 and a newer one on COMIC FUZ. Calling the
    # first a syndicated copy of the second misattributes it and points a reader at the wrong work.
    # A title match alone cannot tell a syndication from a same-named separate run, so the claim is
    # only made where we hold chapter data on the origin side to have matched against.
    for r in releases:
        nwk = norm_work(r.get("work") or "")
        og = origin_of.get(nwk)
        if not og or (r.get("plat_name") or "") not in syndicators or og == r.get("plat_name"):
            continue
        origin_chapters = platform_history.get((nwk, norm_work(og)))
        if not origin_chapters:
            r["same_title_elsewhere"] = og
            r["origin_note"] = (f"a work of this title also appears on {og}. Whether it is the same "
                                f"run is not established — we hold no chapter list on that side to "
                                f"compare, and a shared title is not evidence of a shared work.")
            continue
        r["syndicated"] = True
        r["origin_note"] = (f"carried on {r.get('plat_name')}; originates on {og}, "
                            f"which is where it should be read")

    for r in releases:
        ch = r.get("channel")
        if ch:
            # The platform is the HOST. A channel is a section within it — きららベース is
            # manga.nicovideo.jp/official/kirara/, with no domain of its own — so composing
            # "ニコニコ漫画（きららベース）" invents a source that does not exist and puts it in the
            # platform list beside real ones. Same category error as treating a parallel edition or
            # a reboot as a separate work: a channel is WHERE WITHIN a platform, not another one.
            r["plat_name"] = ch["host"]
            r["channel_name"] = ch["name"]
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

    # Fill from what we already hold. An author belongs to the WORK, so a row that lacks one can
    # take it from any other row for the same work regardless of which adapter found it; access
    # belongs to a chapter, so it only crosses between rows for the same work, platform and
    # episode. This is not inference — it is the same fact, already fetched, not carried across.
    def _author_str(a):
        """An author field is a string in most sources and a list in a few. Anything else — a dict,
        a nested object — is not a name and is not treated as one."""
        if isinstance(a, str):
            return a.strip() or None
        if isinstance(a, list):
            parts = [x.strip() for x in a if isinstance(x, str) and x.strip()]
            return " / ".join(parts) or None
        return None

    author_of, access_of = {}, {}
    # Identity confirmations carry an author that no release record does — 阿佐ヶ谷サキュバス同人物語's
    # 縁山 was established by search and then never reached a row, because those files hold identity
    # rather than releases and nothing read them here.
    for _idf in ("data/source/comparators/resolved-titles.yaml",
                 "data/source/comicfuz/resolved.yaml",
                 "data/source/kadokomi/resolved.yaml",
                 "data/source/nicovideo/resolved.yaml",
                 "data/source/webpages/nicovideo-titles.yaml"):
        _f = pathlib.Path(_idf)
        if not _f.exists():
            continue
        for w in (yaml.safe_load(_f.read_text()) or {}).get("works") or []:
            au = w.get("author") or w.get("author_on_page")
            ti = w.get("title") or w.get("work_title")
            if au and ti:
                author_of.setdefault(norm_work(ti), au)
    for (wk, pn, ek), f in field_facts.items():
        if f.get("author") and wk not in author_of:
            author_of[wk] = f["author"]
        if f.get("access_modes"):
            access_of.setdefault((wk, pn, ek), f["access_modes"])
    # An author is a fact about a work, and a work's author does not expire when the work drops out
    # of a 60-day window. Until now the index was built from releases, so 怪獣ロマンティクス — whose
    # author じぃと is stated plainly by pixivコミック, and which appears in the feed via マガポケ where
    # no author is stated — had an empty author column while the answer sat in a file we had
    # already fetched. Same for アイドラトリィ and オカルトタイムズ. Read every source we hold, once.
    for _f in sorted(pathlib.Path("data/source").rglob("*.yaml")):
        try:
            _d = yaml.safe_load(_f.read_text())
        except Exception:                                                       # noqa: BLE001
            continue

        def _seen(o):
            if isinstance(o, dict):
                t = next((o[k] for k in ("work_title", "title", "name")
                          if isinstance(o.get(k), str) and o[k].strip()), None)
                a = next((_author_str(o[k]) for k in
                          ("author", "authors", "author_on_page", "author_name")
                          if _author_str(o.get(k))), None)
                if t and a:
                    author_of.setdefault(norm_work(t), a)
                for v in o.values():
                    _seen(v)
            elif isinstance(o, list):
                for v in o:
                    _seen(v)
            elif isinstance(o, str) and "<author>" in o:
                # Some sources keep the platform's Atom feed verbatim, which is the strongest form
                # of this fact: the platform's own <author><name> beside its own <title>.
                for m in re.finditer(r"<title>([^<]+)</title>.{0,900}?<author><name>([^<]+)</name>",
                                     o, re.S):
                    author_of.setdefault(norm_work(m.group(1)), m.group(2).strip())
        _seen(_d)
    for r in releases:
        k = norm_work(r.get("work") or "")
        if r.get("author") and k not in author_of:
            author_of[k] = r["author"]
        if r.get("access_modes"):
            access_of.setdefault((k, r.get("plat_name") or r.get("plat"),
                                  norm_work(r.get("ep") or "")), r["access_modes"])
    filled_author = filled_access = 0
    for r in releases:
        k = norm_work(r.get("work") or "")
        if not r.get("author") and author_of.get(k):
            r["author"] = author_of[k]
            r["author_basis"] = "carried from another record of the same work"
            filled_author += 1
        pn = r.get("plat_name") or r.get("plat")
        ak = (k, pn, norm_work(r.get("ep") or ""))
        # A work-level statement applies to every chapter of that work on that platform, so it is
        # consulted only after the chapter-specific one fails to match.
        got = access_of.get(ak) or access_of.get((k, pn, ""))
        if not r.get("access_modes") and got:
            r["access_modes"] = list(got)
            filled_access += 1

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
    by_work_rows = defaultdict(list)
    for r in releases:
        by_work_rows[norm_work(r["work"])].append(r)

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
    # Works the platform itself calls a one-shot. Confirmation records is_oneshot and the release
    # loop typed everything `chapter` regardless, so a one-shot arrived in the feed as an ordinary
    # instalment of a series with one instalment.
    oneshot_works = set()
    _cf = pathlib.Path("data/source/kadokomi/confirmed.yaml")
    if _cf.exists():
        for w in (yaml.safe_load(_cf.read_text()) or {}).get("works") or []:
            if w.get("is_oneshot") and w.get("work_title"):
                oneshot_works.add(norm_work(w["work_title"]))

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
        # A one-shot is a work in one instalment: the start of it and the end of it. Tested before
        # the chapter rules, which were reaching "later chapter of a work attested elsewhere" and
        # labelling 【読切】吸血少女とウンディーネ 新話.
        if r["type"] == "oneshot":
            # Its own kind. A 読切 is not a 新連載 — it is complete on the day it appears, and
            # labelling it as a serialisation starting tells the reader to expect a second chapter.
            r["kind"], r["kind_basis"] = "oneshot", "a one-shot, complete in one instalment"
            continue
        if ONESHOT_RE.search(ep) or ONESHOT_RE.search(r.get("work") or ""):
            r["type"] = "oneshot"
            r["kind"] = "oneshot"
            r["kind_basis"] = "the title says 読切 — a one-shot, not an instalment"
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
        elif n == 1 and not any(
                ep_number(o.get("ep") or "") not in (None, 1)
                and (ep_number(o.get("ep") or "") or 0) > 1
                and o["pub"] < r["pub"]
                for o in by_work_rows.get(norm_work(r["work"]), [])):
            r["kind"], r["kind_basis"] = "new-series", "episode numbered 1"
        elif n == 1:
            # Chapter 1 dated after a later chapter of the same work is not a new series; it is a
            # misdated row. 妖怪殲滅のサイコリリー's 第1話 came back dated today from a rendered page
            # while its 第13話 sat on 07-30 — the pairing had caught a comment timestamp.
            r["kind"] = "new-chapter"
            r["kind_basis"] = ("numbered 1 but the work has a higher-numbered chapter dated "
                               "earlier — the date is not trustworthy, so not read as a start")
            r["kind_inferred"] = True
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
    # Map every SOURCE ROW to its merged entry, not just the one whose raw strings happen to be the
    # bucket's representative. merge_releases groups on a normalised key, so a chapter carried as
    # 「第５０−２話　夢現」 on one platform and 「【第50話(2)】夢現」 on another lands in one bucket with
    # one representative — and the other row then failed the lookup, fell through to is_preferred =
    # True, and 雨夜の月 appeared twice on the same day for the same chapter.
    by_row = {}
    for m in merged:
        for s in m.get("sources") or []:
            r = s.get("_r")
            if r is not None:
                by_row[id(r)] = m
    by_key = {(m["work"], m["episode"]): m for m in merged}
    # Reading quality decides where to send someone only among copies they can actually read.
    # しあわせ鳥見んぐ is best read on COMIC FUZ and its newest chapter there is behind a long
    # paywall while another platform carries it free — pointing at the better image of something
    # the reader cannot open is not a preference, it is a dead end. A free carrier wins; among
    # free carriers, and among paywalled ones, reading_rank decides as before.
    # Read the merge's OWN sources rather than re-deriving keys: a chapter carried on two
    # platforms has two slightly different episode strings, so keying on each row's text matched
    # nothing and the rule silently did nothing.
    switched = 0
    for m in merged:
        srcs = m.get("sources") or []
        free_srcs = [s for s in srcs if (s.get("_r") or {}).get("free")]
        if not free_srcs:
            continue
        best_free = min(free_srcs, key=lambda s: (ranks.get(s["platform"]) or 99,
                                                  s["platform"]))["platform"]
        if best_free == m["preferred"]:
            continue
        pref_row = next((s for s in srcs if s["platform"] == m["preferred"]), None)
        if pref_row and (pref_row.get("_r") or {}).get("free"):
            continue          # the preferred copy is free too; rank keeps its say
        carriers = {s["platform"] for s in srcs} | {m["preferred"]}
        m["also_on"] = sorted(carriers - {best_free})
        m["preferred"] = best_free
        m["preferred_reason"] = "the best-ranked carrier this chapter is actually free on"
        switched += 1
    for r in releases:
        m = by_row.get(id(r)) or by_key.get((r["work"], r["ep"]))
        if m:
            r["preferred"] = m["preferred"]
            r["also_on"] = m["also_on"]
            if m.get("preferred_reason"):
                r["preferred_reason"] = m["preferred_reason"]
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
    # The same chapter can now arrive twice from one platform: its per-series feed and its
    # platform-wide feed both carry it, with different release ids. merge_releases picks the best
    # PLATFORM for a chapter, which does not help when the duplicate is on that platform —
    # 雨夜の月's 第５０−２話 appeared twice on コミックDAYS. Collapse on what identifies a chapter:
    # the work, the episode, and where it was published.
    # A sitemap row is a URL and a date and nothing else. It earns its place only where no richer
    # source covers the work — otherwise it adds an empty row beside a full one for the same
    # platform, which is how マガポケ came to hold 16 titleless rows next to 43 proper ones.
    rich = {(norm_work(r["work"]), r.get("plat_name") or r.get("plat"))
            for r in releases if r.get("basis") != "sitemap" and (r.get("ep") or "").strip()}
    before_thin = len(releases)
    releases = [r for r in releases
                if r.get("basis") != "sitemap"
                or (norm_work(r["work"]), r.get("plat_name") or r.get("plat")) not in rich]
    thin_dropped = before_thin - len(releases)

    # The catch-all resolver is a last resort and behaves like one: it reads whatever markup a page
    # offers, which on コミックFUZ means the 公開予定 strip — chapter numbers against dates months in
    # the future, no access, and the platform name inherited from whichever list named the work.
    # That is right when nothing else reaches a work and wrong the moment something does. コミック
    # FUZ's own adapter holds 一畳間まんきつ暮らし！ with 67 chapters, each with a price and a free_from
    # date; the resolver held the same work with 64 dateless-in-substance rows labelled ニコニコ.
    # Drop the resolver's version wherever a real adapter covers the same work on the same host.
    def host_of(u):
        m = re.match(r"https?://([^/]+)", u or "")
        return m.group(1).lower() if m else ""

    covered = {(norm_work(r["work"]), host_of(r.get("url")))
               for r in releases if r.get("plat") != "remaining" and r.get("access_modes")}
    before_res = len(releases)
    releases = [r for r in releases
                if r.get("plat") != "remaining"
                or (norm_work(r["work"]), host_of(r.get("url"))) not in covered]
    resolver_dropped = before_res - len(releases)

    seen_chapter, deduped, dropped_dupes = {}, [], 0
    for r in sorted(releases, key=lambda r: (r["pub"], r.get("basis") == "heuristic")):
        # The FULL episode title, not episode_key. episode_key reduces to a chapter number, so
        # 第５０−１話 and 第５０−２話 both key as n50 — using it here silently deleted every second
        # part of a split chapter. That is right for deciding "same chapter, two platforms" and
        # exactly wrong for deciding "same row twice".
        k = (norm_work(r["work"]), norm_work(r.get("ep") or ""),
             r.get("plat_name") or r.get("plat"))
        # An empty episode is not an identity: work-level rows (ニコニコ) and comparator claims
        # would all collapse into one per platform. Those are deduped by date instead.
        if not (r.get("ep") or "").strip():
            k = k + (r["pub"],)
        if k in seen_chapter:
            # Merge what the duplicate knows rather than discarding it wholesale. The same chapter
            # arrives from the platform's own feed AND from confirmation, and only the confirmed
            # copy knows it is a one-shot — 下部七花はかく語りき was in the feed as an ordinary
            # chapter because the plain row happened to sort first.
            kept = seen_chapter[k]
            if r.get("type") == "oneshot" and kept.get("type") != "oneshot":
                # The kind was derived before this merge, so upgrading the type alone left
                # 下部七花はかく語りき a one-shot labelled 新話. Upgrade both together.
                kept["type"] = "oneshot"
                kept["kind"] = "oneshot"
                kept["kind_basis"] = "one-shot: the platform lists one episode"
            if r.get("discovered_via") and not kept.get("discovered_via"):
                kept["discovered_via"] = r["discovered_via"]
            # Same for the fields themselves. Two rows for one chapter are two readings of the same
            # page, and the one that sorted first is not necessarily the one that knows more:
            # 吸血少女とウンディーネ arrived from the platform pass with a date and a chapter name, and
            # again from the row-level backfill with the access state read off the series feed. The
            # first won on sort order and the second was discarded whole, access included — so the
            # row stayed empty in exactly the field the second fetch had gone out to fill.
            for f in ("author", "access_modes", "free_from", "url"):
                if r.get(f) and not kept.get(f):
                    kept[f] = r[f]
            dropped_dupes += 1
            continue
        seen_chapter[k] = r
        deduped.append(r)
    releases = deduped
    # `feed_date` is where a release sits in the list; `pub` remains what it always was, the
    # publication date, locked at first sighting and never revised (§5). They differ only for a
    # late discovery, which is news on the day it is found — filing it under a publication date
    # months back would bury it where nobody looks, which is the same as dropping it.
    # A work with other releases inside the window is not newly discovered; only one of its
    # chapters is old. なとりとしずは's 第1話 (2026-05-25) was being lifted to the top of the feed
    # while its 第2話, 第3話 and 第5話 sat in place below — the same work presented twice over, once
    # as news. Surfacing is for works we would otherwise never show at all.
    # ── first-sighting ledger (§5) ────────────────────────────────────────────────────────────
    # "Locked at first sighting and never revised" needs somewhere to remember the sighting. Until
    # this existed, `discovered_on` was read from the source file's `retrieved:` field — which every
    # adapter rewrites on every run. Run by hand every few days that is invisible. On a daily
    # schedule it means a late discovery is discovered again each morning: 吸血少女とウンディーネ,
    # published 2026-05-14 and found in August, would sit at the top of the feed as news for the
    # rest of its life, and so would every one-shot 百合ナビ ever covers late.
    #
    # The ledger is the durable half of this pipeline. Source files are snapshots of what a platform
    # says today and are overwritten wholesale; this is written once per release and never revised,
    # and it is committed, so the sighting survives a rebuild from an empty checkout.
    ledger_path = pathlib.Path("data/ledger/first-seen.yaml")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = {}
    if ledger_path.exists():
        # str() on the value: YAML parses a bare 2026-08-02 into a datetime.date, and mixing those
        # with the string dates everything else uses makes the feed sort raise TypeError. Which it
        # did, silently, because the failure was hidden behind a grep and a pipe's exit code.
        ledger = {k: str(v) for k, v in
                  ((yaml.safe_load(ledger_path.read_text()) or {}).get("first_seen") or {}).items()}
    today_iso = str(datetime.date.today())
    new_sightings = 0
    for r in releases:
        key = f"{norm_work(r['work'])}|{norm_work(r.get('ep') or '')}|{r.get('plat_name') or r.get('plat')}"
        if key not in ledger:
            ledger[key] = today_iso
            new_sightings += 1
        # The ledger wins over the source file's retrieved date, always. A source rewritten today
        # does not make an old release new.
        if r.get("late_discovered"):
            r["discovered_on"] = ledger[key]
    ledger_path.write_text(
        "# When each release was FIRST seen by this pipeline. Written once per release and never\n"
        "# revised (REQUIREMENTS §5). Source files are snapshots and get overwritten every run;\n"
        "# this is the part that has to persist, and it is why the repo — not the working tree —\n"
        "# is the store of record.\n"
        "#\n"
        "# Key: work|episode|platform, normalised. A release whose key changes is a new sighting,\n"
        "# which is the correct behaviour: if the chapter title changed, it is not the row we saw.\n"
        "source: derived\nrole: first-seen-ledger\n"
        f"updated: {today_iso}\ncount: {len(ledger)}\nfirst_seen:\n"
        + "".join(f"  {json.dumps(k, ensure_ascii=False)}: {v}\n"
                 for k, v in sorted(ledger.items())))

    # ── initial build period ───────────────────────────────────────────────────────────────────
    # Surfacing a late discovery at the top of the feed is right in STEADY STATE: a one-shot that
    # 百合ナビ covers weeks late would otherwise be filed months back and never seen. It is wrong
    # NOW. The archive sweep is reading ten years of coverage, and every work it recovers would
    # arrive stamped "discovered today" — a decade of one-shots piled onto one date, drowning the
    # actual news and asserting a discovery event that is an artefact of when we happened to run.
    #
    # During the initial build a work is recorded against the date it was published, which is the
    # date the claim gives. `late_discovered` is still computed and still stored, so the rows can be
    # told apart later and so steady-state behaviour can be restored by flipping this.
    BOOTSTRAP = True
    if BOOTSTRAP:
        for r in releases:
            r["surfaced"] = False
    in_window_works = {norm_work(r["work"]) for r in releases if not r.get("late_discovered")}
    for r in releases:
        if r.get("late_discovered") and norm_work(r["work"]) in in_window_works:
            r["late_discovered"] = False
            r["discovered_on"] = None
    for r in releases:
        r["feed_date"] = (r["pub"] if BOOTSTRAP or not r.get("late_discovered")
                          else (r.get("discovered_on") or r["pub"]))
    releases.sort(key=lambda r: r["feed_date"], reverse=True)

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
    # A candidate stops being a candidate the moment a platform attests it. Nothing removed them,
    # so the queue still listed seven works as "unconfirmed" that the feed had confirmed — the tab
    # persisted with nothing in it that was true.
    _feed_att = {norm_work(r["work"]) for r in releases if r.get("provenance") == "attested"}
    queue, promoted = [], 0
    for f in sorted(glob.glob("data/queue/*.yaml")):
        d = yaml.safe_load(open(f)) or {}
        for c in d.get("candidates") or []:
            if norm_work(c.get("work_title") or "") in _feed_att:
                promoted += 1
                continue
            queue.append({"work": c.get("work_title"), "signal": c.get("signal"),
                          "url": c.get("url"), "headline": c.get("headline"),
                          "announced": str(c.get("announced", "")),
                          "source": d.get("source"), "status": c.get("status")})

    # ── anthologies and other collections ─────────────────────────────────────────────────────
    # A 百合アンソロジー is not a serial and its instalments are not its chapters. Each is a separate
    # short work by a separate author, and 一迅プラス states both in the chapter title:
    # 【試し読み】白玉もち［貝合わせ］ is 貝合わせ by 白玉もち. We were flattening 19 of these into
    # "new chapters" of one work by an author called アンソロジー.
    #
    # THE CAUTION THAT MATTERS: a collection's label does not descend to its instalments. These
    # seven are titled 百合アンソロジー, so the publisher has labelled the collection itself — but a
    # container like 横槍メンゴ新作読切シリーズ is an author's 読切 series where one volume is yuri and
    # the next need not be. Discovery flags the container because ONE instalment matched. Recording
    # the container as a yuri work with N chapters would assert that about all N.
    # Containers are not uniform, and neither is how they name their instalments. Two shapes so far,
    # and the point is that more will appear:
    #
    #   一迅プラス     【試し読み】白玉もち［貝合わせ］     bracketed, marker first
    #   pixivコミック  漫画：樫風 幼馴染のトロフィー(前編)  role-prefixed, title runs on
    #
    # Both state an author and a title for a work that is not the container. Neither fits the
    # chapter model, and both are works.
    ANTHOLOGY_EP = re.compile(
        r"【(?:試し読み|読切|読み切り)】\s*([^［\[]{1,20})[［\[]([^］\]]{1,40})[］\]]"
        r"|(?:漫画|作画|著者)[：:]\s*(\S{1,16})\s+(.{2,40}?)$")

    def anth_parts(s):
        """(author, title) for an instalment, whichever shape the container uses."""
        m = ANTHOLOGY_EP.match((s or "").strip())
        if not m:
            return None
        a, ti = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        a, ti = (a or "").strip(), (ti or "").strip()
        # (前編)/(後編) is a part of the instalment, not a different work — keep the parts together
        # under one title so a two-part 読切 does not become two works.
        ti = re.sub(r"\s*[（(](?:前編|後編|中編|前篇|後篇)[）)]\s*$", "", ti).strip()
        return (a, ti) if a and ti else None
    COLLECTION = re.compile(r"アンソロジー|短編集|読切シリーズ|読み切りシリーズ|読切集|オムニバス|傑作選")
    # An instalment that names its own author and title IS A WORK, and is recorded as one. It does
    # not fit the model cleanly — it has no series id of its own, its URL belongs to the container,
    # and its "platform" is the container's platform — but a 読切 by 白玉もち called 貝合わせ is not a
    # chapter of anything, and filing it as one loses both the work and its author. Where the
    # categories and the thing disagree, the thing wins.
    split_anth = 0
    for r in releases:
        parts = anth_parts(r.get("ep"))
        if not parts:
            continue
        author, title = parts
        r["collection"] = r["work"]
        r["work"], r["author"], r["ep"] = title, author, title
        # One instalment, complete in itself. The container may run for years; this did not.
        r["type"], r["kind"] = "oneshot", "oneshot"
        r["kind_basis"] = "an instalment of a collection, complete in one part"
        split_anth += 1
    for r in releases:
        if COLLECTION.search(r.get("work") or ""):
            r["in_collection"] = True
    print(f"anthology instalments split into their own author and title : {split_anth}")

    # ── series index (data/build/series.json) ─────────────────────────────────────────────────
    # The feed is a 60-day window, which answers "what updated recently". A reader asking "what can
    # I read" wants the other question, and the works most worth listing are exactly the ones the
    # window drops: a long-running series between arcs is absent from the feed and entirely
    # reachable. So this is built from the FULL chapter histories in data/source/ — 19,031 chapters
    # against the feed's 1,387 — and not from `releases`.
    #
    # A row is (work, PLATFORM), not (work). 40 works run on more than one platform and they differ
    # in what is free and how much of it; collapsing them would hide the choice a reader is making.
    # The 単行本 tab is per-work because a volume is; this is not.
    # A row's platform is decided by the HOST it was read from, not by the label a file gave it.
    # The catch-all resolver names a row after whichever list mentioned the work, so remaining.yaml
    # holds 雨夜の月 as マガポケ with a comic-days.com URL and コミックDAYS's whole 121-chapter history
    # — which then merged into マガポケ's genuine 10 chapters and produced a 132-chapter マガポケ row
    # whose access counts were コミックDAYS's. A host cannot be mislabelled; a name can.
    host_plat = {}
    for _f in sorted(pathlib.Path("data/source").rglob("*.yaml")):
        try:
            _d = yaml.safe_load(_f.read_text())
        except Exception:                                                       # noqa: BLE001
            continue
        if not isinstance(_d, dict) or _d.get("platform") == "remaining":
            continue
        _fp = _d.get("platform_name") or _d.get("platform") or ""
        for w in _d.get("works") or []:
            if not isinstance(w, dict):
                continue
            m = re.match(r"https?://([^/]+)", w.get("url") or "")
            pn = w.get("platform_name") or _fp
            if m and pn:
                host_plat.setdefault(m.group(1).lower(), Counter())[pn] += 1
    host_plat = {h: c.most_common(1)[0][0] for h, c in host_plat.items()}

    series = {}
    for _f in sorted(pathlib.Path("data/source").rglob("*.yaml")):
        try:
            _d = yaml.safe_load(_f.read_text())
        except Exception:                                                       # noqa: BLE001
            continue
        if not isinstance(_d, dict) or _d.get("record_type") != "web_work_chapters":
            continue
        # comicfuz and kadokomi predate the platform_name convention and state only `source`.
        _SRC_PLAT = {"comicfuz": "COMIC FUZ", "kadokomi": "カドコミ"}
        _fp = (_d.get("platform_name") or _d.get("platform")
               or _SRC_PLAT.get(_d.get("source"), "") or "")
        for w in _d.get("works") or []:
            title = (w.get("work_title") or "").strip()
            if not title:
                continue
            plat = (w.get("platform_name") or _fp or "").strip()
            _hm = re.match(r"https?://([^/]+)", w.get("url") or "")
            if _hm:
                _byhost = host_plat.get(_hm.group(1).lower())
                if _byhost and _byhost != plat:
                    plat = _byhost
            # A chapter without a date is still a chapter. COMIC FUZ states no updatedDate on its
            # coin chapters at all — 70 of 球詠's 228 — so dropping undated rows made every paid
            # chapter on that platform invisible: the work read as 158 chapters with nothing paid,
            # and the platform as 96% free. Undated chapters count towards length and access; they
            # simply cannot contribute a first or latest date.
            chs = list(w.get("chapters") or [])
            # カドコミ dates a not-yet-released chapter 9999-12-31, and コミックFUZ carries 公開予定
            # rows months out. Neither has been published, so neither can be the latest chapter —
            # left in they sorted the whole index by which series had announced furthest ahead.
            _now = str(datetime.date.today())
            future = [c for c in chs if c.get("updated") and str(c["updated"])[:10] > _now]
            chs = [c for c in chs if not (c.get("updated") and str(c["updated"])[:10] > _now)]
            dated = sorted((c for c in chs if c.get("updated")),
                           key=lambda c: str(c["updated"]))
            # Whether the chapter count is the SERIES length or only what we can see. Some routes
            # are partial by construction and no amount of re-running fixes them: pixivコミック
            # renders only the freely-readable episodes, ガンガンONLINE states a date only for
            # chapters inside a publishing window, マガポケ draws twenty and hides the rest, and a
            # sitemap knows a handful of URLs. Presenting "2 話" for 裏世界ピクニック — which has
            # ninety — would be the interface asserting our coverage as a fact about the manga.
            partial = _d.get("source") in ("sitemap",) or _d.get("platform") in (
                "pixivcomic", "ganganonline", "magapoke", "mangaone", "backfill", "remaining",
                "corocoro") or str(_f).endswith(("sitemap-magapoke.yaml", "magapoke-deep.yaml",
                                                 "rendered-magapoke.yaml", "rendered-mangaone.yaml"))
            # A one-shot is knowable from the record itself, and has to be: almost every 読切 is
            # older than the 60-day feed, so asking the releases about it finds 17 of the 433
            # single-chapter rows. The platform states it in the chapter title (【読切】…) or the
            # confirmation marks the work, and both are already how the feed decides this.
            # ONESHOT_RE over every chapter marks a whole SERIES as a one-shot the moment it runs
            # one 読切 special: it caught 恋する小惑星 at 86 chapters, 阿久津さんは推しに似ている at 37
            # and きみと観たいレースがある at 7. A 読切 is short by definition, so the marker only counts
            # when the work is short too. Three allows for a 前後編 and a little slack; anything
            # longer is a serial that happened to publish one.
            # EVERY chapter must carry the marker, not merely one. That single change separates
            # three cases a length cap alone confuses:
            #
            #   1 chapter,  【読切】…            → a one-shot
            #   2 chapters, 【読切】前編 / 後編    → still one work, published in two parts
            #   3 chapters, 【読切】… then 第2話  → a pilot that got serialised. NOT a one-shot any
            #                                     more, and it stops being one the moment the
            #                                     second chapter lands rather than at some
            #                                     arbitrary length.
            #   86 chapters, one 読切 special    → a serial that published a one-shot once
            #
            # Bootstrapping from a 読切 to a serialisation is a real path, so the test has to be one
            # that reclassifies on its own as the work grows.
            _chs = w.get("chapters") or []
            oneshot_src = bool(w.get("is_oneshot")) or (
                bool(_chs) and all(ONESHOT_RE.search(c.get("title") or "") for c in _chs))
            key = (norm_work(title), plat)
            # The link a reader follows must be a page, and for GigaViewer platforms the work-level
            # url is the Atom feed we harvested — /atom/series/<id>, which serves XML. That was 532
            # of 1145 rows pointing at a document no reader wants. Every chapter carries its own
            # episode URL, so the newest one is both readable and the right destination: someone
            # opening a series from this tab wants the latest chapter, not a landing page.
            _feedish = re.compile(r"/atom/|\.xml($|\?)|/feed/?$")
            _wurl = w.get("url")
            _read = next((c.get("url") for c in reversed(dated) if c.get("url")), None)
            if not _read and _wurl and not _feedish.search(_wurl):
                _read = _wurl
            # Accumulate, do not choose. Two files routinely describe the same (work, platform)
            # and know different things: comic-days-series-feeds holds 下部七花はかく語りき WITH its
            # access state and author, comic-days-confirmed holds the same single chapter with
            # neither. Picking the record with more chapters made that a tie, and a tie fell to
            # whichever file sorted first — so the interface showed no access for a chapter whose
            # access we had already fetched. The feed got this right; this did not.
            bucket = series.setdefault(key, {
                "work": title, "platform": plat, "url": None, "feed_url": None,
                "author": "", "chapters": {}, "upcoming": 0,
                "partial": True, "oneshot_src": False, "_srcs": set(),
            })
            bucket["_srcs"].add(_d.get("platform") or _d.get("source") or "")
            bucket["oneshot_src"] = bucket["oneshot_src"] or oneshot_src
            # Partial only if EVERY source for this row is partial. One full history is enough to
            # make the count real, whatever else also saw a slice of it.
            bucket["partial"] = bucket["partial"] and bool(partial)
            bucket["upcoming"] = max(bucket["upcoming"], len(future))
            if not bucket["author"] and w.get("author"):
                bucket["author"] = w["author"]
            if _wurl and _feedish.search(_wurl):
                bucket["feed_url"] = bucket["feed_url"] or _wurl
            elif _wurl:
                bucket["url"] = bucket["url"] or _wurl
            for c in chs:
                # An instalment that names its own author and title is filed as its own work, not
                # as a chapter of the container. Same reasoning as the feed: 貝合わせ by 白玉もち is a
                # work, and a row saying the container has N chapters says nothing true about it.
                _am = anth_parts(c.get("title"))
                if _am:
                    _au, _ti = _am
                    _k2 = (norm_work(_ti), plat)
                    _b2 = series.setdefault(_k2, {
                        "work": _ti, "platform": plat, "url": None, "feed_url": None,
                        "author": _au, "chapters": {}, "upcoming": 0,
                        "partial": False, "oneshot_src": True, "_srcs": {"collection"},
                        "collection": title,
                    })
                    # The instalment's own episode URL where the container gives one, and the
                    # container's page otherwise. Without this a promoted instalment is a work in
                    # the tab whose source chip links nowhere — Mな王子の愛し方 claimed "readable on
                    # pixivコミック" with no way to reach it.
                    _u2 = c.get("url") or w.get("url")
                    if not _b2.get("url"):
                        _b2["url"] = _u2
                    _b2["chapters"].setdefault(c.get("url") or norm_work(_ti), {
                        "title": _ti, "updated": c.get("updated"), "url": _u2,
                        "access_modes": c.get("access_modes"), "author": _au})
                    continue
                # Name AND date. Keying on the name alone was the fix for a worse bug — mixing URL
                # and name key spaces gave 雨夜の月 242 chapters, every one twice — but a name is not
                # unique within a work: 運命は役に立たない has two instalments both called おまけ, on
                # 2026-05-10 and 2026-07-05, and one of them silently vanished. The date separates
                # them, and two sources describing the same chapter agree on both.
                ck = (norm_work(c.get("title") or ""), str(c.get("updated") or "")[:10]) \
                    if c.get("title") else c.get("url")
                slot = bucket["chapters"].setdefault(ck, {})
                for fld in ("title", "updated", "url", "access_modes", "free_until", "free_from",
                            "author"):
                    if c.get(fld) and not slot.get(fld):
                        slot[fld] = c[fld]

    # Collapse each bucket's merged chapters into the row the interface reads.
    for row in series.values():
        chs = sorted(row.pop("chapters").values(), key=lambda c: str(c.get("updated") or ""))
        row["chapters_list"] = chs
        row["chapters"] = len(chs)
        dated = [c for c in chs if c.get("updated")]
        row["dated"] = len(dated)
        row["first"] = str(dated[0]["updated"])[:10] if dated else None
        row["latest"] = str(dated[-1]["updated"])[:10] if dated else None
        row["latest_ep"] = (dated[-1].get("title") or "").strip() if dated else ""
        row["free"] = sum(1 for c in chs if "free" in (c.get("access_modes") or []))
        row["free_timed"] = sum(1 for c in chs if "free-timed" in (c.get("access_modes") or []))
        row["priced"] = sum(1 for c in chs if "purchase" in (c.get("access_modes") or []))
        if not row["author"]:
            row["author"] = next((c["author"] for c in reversed(chs) if c.get("author")), "")
        # The link is the newest chapter that has one; the work-level url only if it is a page.
        row["url"] = next((c.get("url") for c in reversed(dated) if c.get("url")), None) \
            or next((c.get("url") for c in reversed(chs) if c.get("url")), None) or row["url"]

    # Authors: prefer the index built across every source over whatever a single record carried.
    # Adapters that reach a work sideways often have no author at all, and one stale row carries
    # "くずしろ / 第１−１話　奏音と咲希" — an author with a chapter title welded to it. A string
    # containing a chapter marker is not a name, so it is discarded rather than shown. 第１−１話 is a
    # split chapter and the separator is a full-width minus, so requiring digits immediately before
    # 話 would miss exactly the row this guard exists for.
    _BAD_AUTHOR = re.compile(r"第[0-9０-９][0-9０-９\-−‐–—.．]*[話回巻]|更新日|\d{4}[-/年]")
    for row in series.values():
        if row["author"] and _BAD_AUTHOR.search(row["author"]):
            row["author"] = ""
        if not row["author"]:
            idx = author_of.get(norm_work(row["work"]))
            row["author"] = idx if idx and not _BAD_AUTHOR.search(idx) else ""

    # One-shots the releases already resolved — the platform's own statement, for works recent
    # enough to be in the feed at all. Most 読切 are not, which is why the source records matter more.
    _oneshot = {(norm_work(r["work"]), r.get("plat_name") or r.get("plat"))
                for r in releases if r.get("kind") == "oneshot" or r.get("type") == "oneshot"}
    _oneshot_any = {w for w, _ in _oneshot}

    _today = datetime.date.today()
    for row in series.values():
        # State from the one thing every platform actually tells us: when it last published. Named
        # for what is observed, not inferred — nothing here says 完結, because almost no platform
        # says it and guessing it from silence would be wrong for every series on hiatus.
        _k = (norm_work(row["work"]), row["platform"])
        # A work with ONE chapter whose chapter title is the work's own title is a 読切. Platforms
        # name a one-shot's only episode after the work — 神様やめらんない / 神様やめらんない — and the
        # marker-based test misses every one that does not also print 読切. Those were being filed
        # `dormant`, which reads as abandoned when the thing is simply finished.
        _self_named = (row["chapters"] == 1 and not row["partial"]
                       and norm_work(row.get("latest_ep") or "") == norm_work(row["work"]))
        row["oneshot"] = (row.pop("oneshot_src", False) or _k in _oneshot or _self_named
                          or (row["chapters"] == 1 and not row["partial"]
                              and norm_work(row["work"]) in _oneshot_any))
        if not row["latest"]:
            row["state"] = "unknown"
        elif row["oneshot"]:
            row["state"] = "oneshot"
        else:
            age = (_today - datetime.date.fromisoformat(row["latest"])).days
            row["age_days"] = age
            row["state"] = "active" if age <= 45 else ("slow" if age <= 365 else "dormant")
    # Where a work runs on several platforms, each row says so, so a reader on one can see the rest.
    _by_work = defaultdict(list)
    for (wk, plat), row in series.items():
        _by_work[wk].append(plat)
    for (wk, plat), row in series.items():
        row["also_on"] = sorted(p for p in _by_work[wk] if p and p != plat)

    # Scope. An adapter fetching a platform's per-series feeds reads whatever the platform lists,
    # so this walk picks up neighbours of the works we track — 「タイムマシンはお呼びでない!」 arrived
    # that way. The tracked universe is the candidate list plus whatever is already in the feed;
    # anything outside it was never assessed as in scope and does not belong in a reader-facing tab.
    _cands = set()
    _ct = pathlib.Path("data/coverage/claim-targets.yaml")
    if _ct.exists():
        for c in (yaml.safe_load(_ct.read_text()) or {}).get("candidates") or []:
            if c.get("title"):
                _cands.add(norm_work(c["title"]))
    # The catch-all resolver labels a row with whichever list named the work, not with the host it
    # actually read: it holds 雨夜の月 as マガポケ with 121 chapters, which is コミックDAYS's history
    # wearing another platform's name. The feed already drops these; so must this, or the tab
    # invents a second platform for a work and reports the wrong access alongside it.
    _real = defaultdict(int)
    for (wk, plat), row in series.items():
        if row["_srcs"] != {"remaining"}:
            _real[wk] = max(_real[wk], row["chapters"])
    series = {k: v for k, v in series.items()
              if v["_srcs"] != {"remaining"} or v["chapters"] > _real[k[0]]}

    _cands |= {norm_work(r["work"]) for r in releases}
    # An instalment is in scope because the collection it appeared in was assessed, not because a
    # discovery list names it — 貝合わせ appears on no candidate list and is nonetheless a work we
    # hold, attested, with its own author.
    _cands |= {norm_work(v["work"]) for v in series.values() if v.get("collection")}
    _before = len(series)
    series = {k: v for k, v in series.items() if k[0] in _cands}
    _out_of_scope = _before - len(series)

    for row in series.values():
        row.pop("_srcs", None)
        row.pop("chapters_list", None)
    # ── collapse platforms into one work ───────────────────────────────────────────────────────
    # A reader looking for 雨夜の月 wants the work, with its platforms as ways in — not three rows
    # competing to be it. The rows differ in COVERAGE, not in what they are: コミックDAYS holds 121
    # chapters, マガポケ 10, ヤンマガWeb 4, and presenting those as three series implies three
    # different lengths for one story.
    #
    # Grouping is by title, with the two dangerous cases declared rather than guessed:
    #   distinct  same title, different works (a reboot). Kept apart.
    #   editions  one work in parallel formats (a 縦読み version). Grouped, format recorded, and the
    #             chapter counts NOT summed — both editions carry the same story.
    # Neither is inferable. Date-span disjointness flags 57 pairs here and every one is the same
    # work seen through different coverage windows.
    _ov = pathlib.Path("data/identity/distinct-titles.yaml")
    distinct, editions = set(), {}
    if _ov.exists():
        _od = yaml.safe_load(_ov.read_text()) or {}
        distinct = {norm_work(x["title"]) for x in (_od.get("distinct") or []) if x.get("title")}
        for e in _od.get("editions") or []:
            if e.get("title") and e.get("platform"):
                editions[(norm_work(e["title"]), e["platform"])] = e.get("format") or "vertical"

    works_out, by_title = [], defaultdict(list)
    for row in series.values():
        row["format"] = editions.get((norm_work(row["work"]), row["platform"]), "standard")
        key = norm_work(row["work"])
        by_title[key if key not in distinct else f"{key}|{row['platform']}"].append(row)

    for _k, rows in by_title.items():
        rows.sort(key=lambda r: (r["chapters"], r["latest"] or ""), reverse=True)
        best = rows[0]
        works_out.append({
            "work": best["work"],
            "author": next((r["author"] for r in rows if r["author"]), ""),
            # The BEST-KNOWN length, not a sum: every source is describing the same story, and
            # adding them would report 135 chapters for a 121-chapter work.
            "chapters": best["chapters"],
            "partial": all(r["partial"] for r in rows),
            "latest": max((r["latest"] for r in rows if r["latest"]), default=None),
            "latest_ep": best["latest_ep"],
            "first": min((r["first"] for r in rows if r["first"]), default=None),
            "state": best["state"], "oneshot": best["oneshot"],
            "collection": best.get("collection"),
            "url": best["url"],
            "free": best["free"], "free_timed": best["free_timed"], "priced": best["priced"],
            "sources": [{"platform": r["platform"], "url": r["url"], "chapters": r["chapters"],
                         "free": r["free"], "free_timed": r["free_timed"], "priced": r["priced"],
                         "latest": r["latest"], "partial": r["partial"], "format": r["format"]}
                        for r in rows],
        })
    series_rows = sorted(works_out,
                         key=lambda r: (r["latest"] or "", r["chapters"]), reverse=True)
    (out / "series.json").write_text(json.dumps(
        {"series": series_rows,
         "generated": str(_today),
         "note": "Built from full chapter histories in data/source/, not from the 60-day feed "
                 "window. One row per WORK; its platforms are listed as sources, because they "
                 "differ in coverage rather than in what they are.",
         "thresholds": {"active": "latest chapter within 45 days",
                        "slow": "within a year", "dormant": "older than a year"}},
        ensure_ascii=False, indent=1, default=jsonable))
    _st = Counter(r["state"] for r in series_rows)
    print(f"series index    : {len(series_rows)} (work, platform) rows across "
          f"{len({k[0] for k in series})} works — {dict(_st)}"
          f"{f'  [{_out_of_scope} out-of-scope rows dropped]' if _out_of_scope else ''}")

    (out / "feed.json").write_text(json.dumps(
        # The queue is a worklist, not part of the published database, and it is not shipped.
        # It lived behind a 候補 tab that showed candidates already confirmed; the project owner's
        # call is that it should not be in the interface at all. data/queue/ stays as the internal
        # worklist it always was.
        {"releases": releases, "platforms": platforms,
         # Works a comparator reports as updating that the platform's own full chapter history
         # contradicts. Recorded rather than silently dropped: they are not coverage we lack.
         "contradicted": contradicted_works,
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
    print(f"duplicate chapters collapsed : {dropped_dupes}")
    print(f"thin sitemap rows superseded  : {thin_dropped}")
    print(f"resolver rows superseded      : {resolver_dropped}")
    print(f"fields carried across records : {filled_author} author, {filled_access} access")
    print(f"preference moved to a free carrier : {switched}")
    print(f"claims contradicted by the platform's own history : {contradicted}")
    serialised = sum(1 for r in releases if r.get("web") == "serialised")
    print(f"releases        : {len(releases)} from {len(platforms)} platform(s) "
          f"({serialised} serialised, {len(releases)-serialised} promotional samples)")
    print(f"print candidates: {len(print_candidates)} from web samples")
    wl = sum(1 for w in web_works if w.get("marketing_label") == "yuri")
    print(f"web works       : {len(web_works)} confirmed ({wl} with a publisher yuri label)")
    print(f"queue           : {len(queue)} unconfirmed candidates "
          f"({promoted} dropped — now attested)")
    print(f"works compiled  : {len(works)}")
    print(f"volumes         : {sum(w['volume_count'] for w in works)}")
    print(f"with openBD     : {sum(1 for w in works if 'openbd' in w['sources'])}")
    print(f"unclassified    : {len(warnings)} works have no content_tier (needs human review)")
    print(f"written         : {out}/works.json, {out}/index.json")


if __name__ == "__main__":
    main()
