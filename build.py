#!/usr/bin/env python3
"""Merge source layers, validate, and compile the published dataset.

Source records (data/source/<source>/) are stored as fetched and never edited. Curation lives in
data/overlay/ and always wins. This step merges them by source priority, enforces the validation
rules in REQUIREMENTS §6, and writes data/build/.

Fails closed: any validation error aborts the build without writing.

Usage:  build.py [--out data/build]
"""
import argparse, datetime, glob, json, pathlib, re, statistics, sys, unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, "adapters")
from crossplatform import carriage, episode_key, merge_releases  # noqa: E402

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
import checkstate  # noqa: E402
import importdates  # noqa: E402

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
# A finale, said in the title. 最終話 and its variants, and a bracketed 完 in any of the brackets
# Japanese publishers reach for: 男装メイドは尽くしたい ends 4話②＜完＞ and read as dormant for a
# year because only round brackets were accepted. Not anchored to the end, because マンガPark's
# listing appends view counts to the title (`4話②＜完＞ 23 24`) and an anchor made the marker
# invisible on the one source that dates the work correctly. The bracket pair is specific enough
# to carry it: across every chapter we hold, exactly two works match, and both have ended.
# 完全版 and similar cannot match, because the closing bracket must follow the 完 itself.
# Sites that publish a read-through of a book they are selling, an instalment at a time, and look
# exactly like a serialisation to a scraper. ダ・ヴィンチニュース numbers them 第1回, 第2回 and one
# of them says 全4回連載でお届けします outright: it is a 試し読み of a finished tankobon, not the
# work's publication. Counted as chapters they gave 三角形の壊し方 eleven instalments and a run of
# dates that decided its state. Book shops elsewhere do the same thing with tidier markup, so this
# list is expected to grow rather than to have caught them all.
#
# コミックノヴァ was on this list on the strength of looking similar, and it does not belong: it is
# 一二三書房's own weekly serialisation, numbered 第N話, which withdraws older chapters with
# 「公開は終了しました」. That is why our capture of it looks thin, and thin is not promotional.
PROMO_HOSTS = ("ddnavi.com",)

FINAL_RE = re.compile(r"最終(話|回|幕|エピソード)|[（(＜<〈\[【]\s*完\s*[）)＞>〉\]】]")
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

# A COMPETITION ENTRY. 【第28回角川漫画新人大賞】佳作 is a prize citation standing where a chapter
# name goes. It is not a chapter name and, crucially, the 28 is the twenty-eighth CONTEST rather
# than the twenty-eighth chapter, so ep_number read it as one and four works were filed as later
# chapters of series that do not exist. Each is a single instalment, which is what a newcomer prize
# publishes: the entry itself.
#
# COUNTER-CASES DECIDED THE SHAPE, and a keyword list alone got four of ten wrong. Across the 11,201
# chapter names held, a bare award vocabulary also matched:
#
#   第11話 2021年12月29日 東京大賞典(GⅠ)     大賞 inside 大賞典, a horse race
#   第1回 …最後のコンクールで片桐は…          a music competition as the story's subject
#   第23話①：歌唱コンテスト                  a chapter about a singing contest
#
# Two things separate a citation from a story: it sits INSIDE BRACKETS (or is the whole title, as
# with カドマンGP受賞作), and it carries no chapter counter. 第N回 is not a usable signal either
# way, since it numbers both contests and chapters.
_AWARD = (r"新人賞|新人大賞|漫画大賞|マンガ大賞|コンテスト|コンクール|佳作|奨励賞|入選|特別賞|受賞")
PRIZE_BRACKETED = re.compile(r"[【（(\[][^】）)\]]*(?:" + _AWARD + r")[^】）)\]]*[】）)\]]")
PRIZE_WHOLE = re.compile(r"^[^。、]{0,24}(受賞作|入選作)$")


# NOT CHAPTER_NUM_RE, which counts 第N回 as a chapter number. 回 numbers both chapters and
# contests, so it is exactly the character that cannot decide this: 【第28回…大賞】 is the
# twenty-eighth contest and 第1回 elsewhere is chapter one. 話 is unambiguous, so only 話 is used.
UNAMBIGUOUS_CHAPTER = re.compile(r"第[0-9０-９]+話|[0-9０-９]+話|#[0-9０-９]+")


def is_prize_entry(title):
    """A competition citation standing where a chapter name goes."""
    t = unicodedata.normalize("NFKC", title or "")
    if UNAMBIGUOUS_CHAPTER.search(t):
        return False
    return bool(PRIZE_BRACKETED.search(t) or PRIZE_WHOLE.match(t))

# A SKIPPED RELEASE SLOT, attested by the publisher.
#
# Japanese web platforms commonly post an illustration in the update slot instead of a chapter,
# and it arrives in the feed as an ordinary episode entry with a date. 休載イラスト is the usual
# form: オトメの帝国 has eleven of them running from 2019 to 2026. Read as chapters they inflate
# the count, can take over `latest`, and would surface to a reader as an update that is precisely
# an announcement of no update.
#
# A skipped slot says ONE scheduled period passed without a chapter. It does NOT say the series is
# on hiatus: for a monthly title that is routine. It is also evidence of LIFE rather than absence,
# because somebody drew the illustration and somebody published it on schedule, which is more than
# silence tells you.
#
# COUNTER-CASES DECIDED THE PATTERN. Keying on お休み alone would be wrong: five of the nine
# non-illustration matches in the corpus are story titles rather than announcements:
# 第８３話　エリザベートお休み中, 第20話 前編　ルイくんのお休み, #14 #お休みしゅる. So お休み counts
# only with a scheduling word in front of it, and a chapter number anywhere in the title settles
# the entry as a chapter whatever else it says.
SKIPPED_RE = re.compile(r"休載|(?:今週|今回|今月|来週|しばらく)は?お休み")
CHAPTER_NUM_RE = re.compile(r"第[0-9０-９]+[話回]|[0-9０-９]+話|#[0-9０-９]+")
# How long an attested skip keeps describing the present. A 休載 notice from 2023 with nothing
# since has stopped being news about a hiatus and is just an old fact, so the state falls back to
# the observed ladder and the notice stays as dated evidence.
HIATUS_FRESH_DAYS = 180


def host_platforms(platforms):
    """host -> the one platform that owns it, for hosts owned by exactly one.

    A host with two claimants is not authoritative and is left out: comic-walker.com carries
    カドコミ and other KADOKAWA brands, so the URL alone cannot say which of them a page belongs
    to. Only the unambiguous ones are used to correct a label.
    """
    import collections
    seen = collections.defaultdict(set)
    for p in platforms:
        if p.get("host") and p.get("name"):
            seen[p["host"]].add(p["name"])
    return {h: next(iter(n)) for h, n in seen.items() if len(n) == 1}


def platform_of(url, owners):
    """The platform a URL is on, where that is unambiguous."""
    if not url or "://" not in str(url):
        return None
    return owners.get(str(url).split("/")[2])


_STATED = {}


def _stated_for(work, platform):
    """The schedule a platform states for a work, if it states one."""
    return _STATED.get((norm_work(work or ""), norm_work(platform or "")))


def _basis_of(best, rows, field):
    """The reason for the state we are publishing, taken from the row that state came from.

    `best` first, because that is the row `state` is read off. Falling back to another row only
    where it agrees about the state, so a basis never explains a different platform's answer.
    """
    if best.get(field):
        return best[field]
    return next((r.get(field) for r in rows
                 if r.get(field) and r.get("state") == best.get("state")), None)


def _with_cadence_date(stated, latest):
    """Turn a stated rhythm into the date it next puts an update on.

    The rhythm is the platform's own words (毎月第3金曜), and turning words into a date needs the
    reader to know what a third Friday is. That belongs here rather than in the browser, where the
    logic would be a second implementation of something already written and tested.

    Only where the platform has not simply named a date, which is better evidence and needs no
    arithmetic at all. A rhythm that pins no particular day (隔週金曜 names a fortnight without
    saying which) yields nothing, which is the honest answer.
    """
    if not stated or stated.get("next_update") or not stated.get("cadence") or not latest:
        return stated
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters" / "render"))
    import schedule_text
    start = datetime.date.fromisoformat(latest) + datetime.timedelta(days=1)
    for k in range(70):
        d = start + datetime.timedelta(days=k)
        if schedule_text.fits(stated["cadence"], d.isoformat()):
            return dict(stated, next_from_cadence=d.isoformat())
    return stated


def _sched_fits(cadence, when):
    """Whether a date falls where a stated cadence puts an update. See render/schedule_text.py."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters" / "render"))
    import schedule_text
    return schedule_text.fits(cadence, when) is True


def load_platform_history(files):
    """(work, platform) -> the dates that platform lists for that work, from whole-history sources.

    ONLY WHOLE HISTORIES. Absence of evidence is evidence of absence just where the list is known
    to be complete. A source that shows what it happens to carry can attest a chapter and must
    never be used to deny one, which is why this is a named list of files rather than everything
    under data/source.

    TWO SHAPES, and the second is what was being dropped. Most files name their platform once at
    the top. A file assembled across platforms (remaining.yaml, claim-resolved.yaml) leaves that
    empty and names the platform on each work instead. The earlier version read only the file-level
    field, so every work in those files keyed on the empty string, matched no claim, and vanished
    without a word. That is why 28 claims read as untraced while their evidence was on disk.
    """
    owners = host_platforms(
        (yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text()) or {}).get("platforms", []))
    out, misfiled = {}, []
    for f in files:
        d0 = yaml.safe_load(open(f)) or {}
        filewide = d0.get("platform_name") or ""
        for w in d0.get("works") or []:
            ti = norm_work(w.get("work_title") or w.get("title") or "")
            label = w.get("platform_name") or filewide
            # THE PLATFORM IS WHERE WE READ, not where somebody said the work was. The adapters
            # label a history with the platform the CLAIM named while following whatever URL
            # actually answered, so a コミックDAYS run arrived filed under マガポケ. That is an
            # attestation wearing an inference's label, and it is worse than a missing one: a
            # history can then refute a claim about a platform it never came from. Eleven rows
            # were wrong this way, and one of them made a live series look dead for 122 days.
            owner = platform_of(w.get("url"), owners)
            if owner and label and norm_work(owner) != norm_work(label):
                misfiled.append((w.get("work_title"), label, owner, w.get("url")))
            pn = norm_work(owner or label)
            ds = sorted({str(c.get("updated"))[:10] for c in (w.get("chapters") or [])
                         if c.get("updated")})
            if not (ti and pn and ds):
                continue
            # A work may appear in several files. Keep the fullest history, because the denial
            # branch asks how much we hold, and a thin copy displacing a full one would turn a
            # refutable claim back into an open one.
            if len(ds) >= len(out.get((ti, pn), ())):
                out[(ti, pn)] = ds
    for t, lab, own, u in misfiled:
        print(f"  note: {t} was filed under {lab} and read from {own} ({u}); using {own}")
    return out


def fold_map(records, fold):
    """Key records by their folded name, keeping the fullest where several fold together.

    A dict comprehension here let the last writer win, and the winner depended on iteration order.
    彼氏の女友達がぐいぐい来る(私に) is held twice, once with full-width brackets and once without,
    and the copy that arrived second carried no English name: a curated translation was written to
    the store, applied cleanly, and then silently dropped on the way to the page. The name was
    absent from the site with nothing anywhere reporting a problem.

    Fullest means the record answering the most questions a reader can ask of it. Ranking by field
    count rather than by which spelling looks canonical avoids deciding that full-width brackets
    are wrong, which they are not; the two spellings are one work and either may be the one a
    source used.
    """
    best, lost = {}, {}
    for k, v in records.items():
        f = fold(k)
        if f in best:
            lost[f] = lost.get(f, 0) + 1
        if f not in best or _fullness(v) > _fullness(best[f]):
            best[f] = v
    return best, sorted(lost.items())


# How much a claim about an English name is worth, highest first. The same order as the name
# store's own rank, restated here because build.py must not import from the resolver.
_EN_BASIS = {"official-jp": 4, "licensed": 3, "translated": 2, "stated": 2, "romaji": 1}


def _fullness(rec):
    """How much a name record actually says, for choosing between two that fold together.

    Field count alone was wrong the moment both records had an `en`. 見えてますよ！愛沢さん is
    held twice, and the copy carrying a curated translation lost to one carrying a community
    database's string, because the loser also happened to hold a reading, a ruby split and a set
    of furigana spans. Counting fields measured the wrong thing: what matters first is WHICH
    English name, and only then how much else is attached.
    """
    if not isinstance(rec, dict):
        return (0, 0, 0)
    has_en = 1 if rec.get("en") else 0
    rank = _EN_BASIS.get(rec.get("basis"), 0) if has_en else 0
    rest = sum(1 for v in rec.values() if v not in (None, "", [], {}))
    return (has_en, rank, rest)


def set_aside(works_out, kadokomi="data/source/kadokomi/chapters.yaml", sources="data/source"):
    """Works that reach the reader as nothing, and why. Returns {work: reason}.

    A row carrying no chapters is not always a gap in our fetching. Three kinds turned out to be
    finished states wearing the same face, and each was sitting in the web list as work somebody
    might go and do.

    A SHOP LISTING. カドコミ lists KADOKAWA's catalogue whether or not a work was ever serialised
    on the web. Searching five: やがて君になる ran in 月刊コミック電撃大王 and finished in 2019,
    繭、纏う in コミックビーム, からふるキューシート！ in 電撃だいおうじ, all print and all complete;
    気になってる人が男じゃなかった is posted on its author's own social accounts. None was published
    on カドコミ. The test is the platform's own serializationStatus, which reads `unknown` for 144
    of the 145 works it lists no episodes for and carries a real value for 175 of the 189 it does.

    AN ANTHOLOGY WHOSE STORIES ARE THEIR OWN ROWS. pixivコミック lists 君は光 and 幼馴染のトロフィー
    under a collection title, and build.py files each under its real author, so the container ends
    up holding nothing because everything in it is somewhere better.

    AN ANTHOLOGY PUBLISHED AS A TASTER. 一迅プラス's are 試し読み throughout, and a promotional
    sample is not a release (REQUIREMENTS §5), so the whole list drops and the book itself is a
    thing to buy rather than to read there.

    ONLY WHERE THAT IS THE WHOLE STORY. A work carrying any other source keeps its place, because
    the claim is about what WE hold rather than about the work: 高音さんと嵐ちゃん updates twice a
    week on ニコニコ漫画 and is in this set, because the one episode that platform shows us
    produced no chapters.
    """
    shelf = set()
    kp = pathlib.Path(kadokomi)
    if kp.exists():
        shelf = {norm_work(w.get("work_title") or "")
                 for w in (yaml.safe_load(kp.read_text()) or {}).get("works") or []
                 if not (w.get("chapters") or w.get("episodes")) and w.get("status") == "unknown"}

    # Works every one of whose listings is a shop's read-through of a book it sells.
    promo_only, promo_seen = {}, set()
    # What each source lists for a work, whether or not any of it survived to a release.
    listed = {}
    for f in glob.glob(f"{sources}/**/*.yaml", recursive=True):
        try:
            d0 = yaml.safe_load(pathlib.Path(f).read_text())
        except Exception:
            continue
        if not isinstance(d0, dict):
            continue
        for w in d0.get("works") or []:
            if isinstance(w, dict) and (w.get("chapters") or w.get("episodes")):
                _nw = norm_work(w.get("work_title") or "")
                listed.setdefault(_nw, []).extend(w.get("chapters") or w.get("episodes"))
                _is_promo = any(h in (w.get("url") or "") for h in PROMO_HOSTS)
                promo_seen.add(_nw)
                promo_only[_nw] = promo_only.get(_nw, True) and _is_promo

    out = {}
    for r in works_out:
        if r.get("chapters"):
            continue
        nw = norm_work(r.get("work") or "")
        plats = {s.get("platform") for s in (r.get("sources") or [])}
        if nw in shelf and plats <= {"カドコミ"}:
            out[r["work"]] = "a カドコミ shop listing for a work it does not serialise"
            continue
        if promo_only.get(nw) and nw in promo_seen:
            out[r["work"]] = "a book shop's 試し読み read-through, not a serialisation"
            continue
        chs = listed.get(nw) or []
        if not chs:
            continue
        titles = [str(c.get("title") or "") for c in chs]
        if all(t.strip().startswith("【試し読み") for t in titles):
            out[r["work"]] = "an anthology published here only as 試し読み samples"
        elif all(anth_parts(t) for t in titles):
            out[r["work"]] = "an anthology whose stories are filed under their own authors"
    return out



def content_flags():
    """Works a source has flagged on content grounds, whether or not we act on the flag.

    HOW THIS WENT WRONG, because the shape recurs. adapters/kadokomi/confirm.py has written
    data/source/kadokomi/withheld.yaml since the first run, flagging works whose `ratingLevel` is
    `adult`, its header saying they are not published. Nothing read the file. All five were live on
    the public site, and no count anywhere said otherwise: a register that nothing consumes is
    worse than no register, because it reads as a control that is working.

    WHAT THE POLICY IS NOW, per the project owner. Every platform in this database is a commercial
    publisher's own web arm, and a reader following a link to a serialisation there is not going to
    meet unwanted pornographic content, certainly not up front. So a rating flag on such a platform
    does not withhold anything. It is RECORDED and REPORTED instead, so that a less obvious future
    case cannot fall permanently between the cracks.

    A flag withholds only where its entry says `withhold: true`. That is the deliberate,
    reviewed decision, and there are none today.

    The count is surfaced in run.json and on status.html, and check.py fails if a flag exists that
    nothing reports. That is the part that could not fail silently a second time.
    """
    out = {}
    for f in sorted(pathlib.Path("data/source").rglob("withheld.yaml")):
        d = yaml.safe_load(f.read_text()) or {}
        for w in d.get("works") or []:
            t = w.get("work_title")
            if t:
                out[norm_work(t)] = {"title": t, "reason": w.get("reason"),
                                     "source": d.get("source") or f.parent.name,
                                     "withhold": bool(w.get("withhold"))}
    return out


def withheld_works():
    """Only the flags a person has decided to act on. Empty is the normal state."""
    return {k: v for k, v in content_flags().items() if v["withhold"]}


# A title that is BOTH adult-marketed and a collection. Both are required: えっち or セフレ alone
# appears in story titles, and アンソロジー alone is most of the anthologies we carry. Together they
# describe how a volume is sold, which is the thing DEFINITIONS §7 turns on.
ADULT_MARKETED = re.compile(r"えっち|エッチ|セフレ|エロ|官能|18禁|R-?18|成人向")
COLLECTION_MARK = re.compile(r"アンソロジー|短編集|傑作選|オムニバス|読切集")


def marketing_flags(series_rows):
    """Adult-marketed collections, REPORTED and published.

    一迅プラス publishes explicit yuri anthologies and exposes no rating field, so nothing else in
    the pipeline can see them. They are not pornography by §7's test and the project owner has
    decided they are safe to carry and to link to, which settles what happens to them. What was
    missing is that nothing would have SHOWN them: a category decided once and then invisible is
    how the withheld register went five works wrong for the life of the project.

    So they appear in the flag report with everything else, marked published, and a fourth arriving
    from a publisher nobody has thought about turns up in the same place rather than nowhere.
    """
    out = {}
    for r in series_rows:
        w = r.get("work") or ""
        if ADULT_MARKETED.search(w) and COLLECTION_MARK.search(w):
            out[norm_work(w)] = {"title": w, "source": "marketing signal",
                                 "reason": "adult-marketed collection; §7 explicit, not pornography",
                                 "withhold": False}
    return out


# An anthology instalment names its own author and title, in one of two shapes. Lifted out of
# main() so it can be tested: a pattern that decides what counts as a WORK is exactly the kind of
# thing that must be provable, and inside a 2,900-line function it was reachable by nothing.
ANTHOLOGY_EP = re.compile(
    r"【(?:試し読み|読切|読み切り)】\s*([^［\[]{1,20})[［\[]([^］\]]{1,40})[］\]]"
    r"|(?:漫画|作画|著者)[：:]\s*(\S{1,16})\s+(.{2,40}?)$")

def anth_parts(s):
    """(author, title, is_trial) for an instalment, whichever shape the container uses."""
    s = (s or "").strip()
    m = ANTHOLOGY_EP.match(s)
    if not m:
        return None
    # WHICH MARKER MATCHED IS PART OF THE ANSWER. 【試し読み】白玉もち［貝合わせ］ names a real
    # work by a real author, so splitting it is right; but what is on the WEB is a preview of
    # a printed volume, not a serialisation of that work. Both facts are true at once and the
    # split was keeping only the first, so 28 previews were published as web works and 13 of
    # them reached the feed as releases.
    is_trial = s.startswith("【試し読み")
    a, ti = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    a, ti = (a or "").strip(), (ti or "").strip()
    # (前編)/(後編) is a part of the instalment, not a different work — keep the parts together
    # under one title so a two-part 読切 does not become two works.
    ti = re.sub(r"\s*[（(](?:前編|後編|中編|前篇|後篇)[）)]\s*$", "", ti).strip()
    return (a, ti, is_trial) if a and ti else None


def is_skipped_slot(title):
    """One producer of this fact, used by the release classifier and the series accumulator alike."""
    t = unicodedata.normalize("NFKC", title or "")
    return bool(SKIPPED_RE.search(t)) and not CHAPTER_NUM_RE.search(t)
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


# ── Extracted from main() ────────────────────────────────────────────────────────────────────
#
# main() was 2200 of this file's 2372 lines and bound 291 local names, 41 of them more than 300
# lines apart — `r` is rebound 68 times across a span of 2166. That is not untidiness, it is a
# mechanism: a fresh name at the bottom silently captures one bound near the top, and nothing
# warns. It happened twice in one hour, both times in the code below. `works` was reused as a set
# of titles, turning 302 dicts into strings; `warnings` was reused by the archive block, so a line
# reporting "302 works have no content_tier" quietly reported 0 and real outstanding work read as
# done.
#
# These two blocks are the tail of the pipeline and are pure in the useful sense: they read the
# finished data and write files. Out of main() they get their OWN scope, so a name bound here
# cannot collide with one bound a thousand lines earlier, and the parameter list states exactly
# what each needs instead of "whatever happens to be in scope".
#
# Verified by byte-comparing every file in data/build/ before and after: identical.

# ── English names and readings ────────────────────────────────────────────────────────────────
#
# The store holds a KANA reading, never a romanised string (NAMES-PLAN §8.1): Yūri, Yuuri and Yuri
# are all derivable from kana and none from each other. The reader chooses a style, so the build
# renders all three here rather than shipping a romanisation engine to the browser — the stored
# form stays kana and nothing is baked.
#
# Only what the plan permits is emitted. A title's English name is shown unmarked when it is the
# work's own (official-jp) or a licensor's (licensed), and marked when it is ours (translated,
# romaji). An unverified reading is marked — §5d, and see the memory note: this is NOT a return of
# 要確認, because it is a fact about the name that a Japanese-literate reader can adjudicate, and it
# exists so a real person is not authoritatively misnamed. Anything with no rendering emits nothing
# at all and the interface shows the Japanese (§6).
def load_names():
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters" / "names"))
        import kana as _kana
    except Exception:
        return {}, {}
    try:
        import pass4_analyser as _p4
    except Exception:
        _p4 = None

    def render(k_ja, rec, is_person=False):
        out = {}
        rd = rec.get("reading")
        if rd:
            out["reading"] = rd
            # Furigana per KANJI RUN, not stacked over the whole title. pass 4 stores spans it
            # aligned with the tokeniser; a reading that came from a source has no token structure,
            # so it is aligned directly — the anchor algorithm works on a whole string too, it is
            # simply less accurate than doing it per token.
            # THE RUBY MUST SPELL THE READING. Spans and readings are produced by different paths
            # — the analyser tokenises, while a sourced reading arrives whole — and nothing forced
            # them to agree. Three records ended up reading ワタシ while their ruby said わたくし,
            # which is one record contradicting itself on the same line of the page.
            #
            # So stored spans are used only when they reconstruct the stored reading. Otherwise the
            # reading wins, because it is the thing other passes corroborate and the thing the
            # romanisation is built from, and the ruby is re-derived from it.
            sp = rec.get("furigana_spans")
            if sp and not _kana.ruby_spells(sp, rd):
                sp = None
            if not sp:
                got = _kana.align(k_ja, rd.replace(" ", ""))
                if got:
                    sp = [[t, _kana.to_hiragana(x) if x else None] for t, x in got]
            # JUKUGO-RUBY, where the split can be established. The layout rules distinguish a
            # reading placed over a whole compound (group-ruby) from one where each character
            # carries its own (jukugo-ruby), and prefer the latter: it puts じょう over 情 rather
            # than over 純情, and it gives the line somewhere to break. Where the split cannot be
            # worked out the run stays a group, which is the fallback the rules themselves name.
            if sp:
                _exp = []
                for _t, _x in sp:
                    _parts = _kana.jukugo_split(_t, _x) if _x and len(_t) > 1 else None
                    if _parts:
                        _exp.extend([[_c, _kana.to_hiragana(_r)] for _c, _r in _parts])
                    else:
                        _exp.append([_t, _x])
                sp = _exp
            if sp and any(x[1] for x in sp):
                out["ruby"] = sp
            # Personal names take particles=False — と in a name is 都 or 斗, never the particle.
            # latinise here too. It was applied to `en` and not to the romanisations, so a title
            # whose reading romanised cleanly could still ship its Japanese punctuation — ｜ in
            # コミックオギャー)｜… survived every pass because this one output skipped the step.
            out["romaji"] = {st: (_p4.latinise if _p4 else (lambda x: x))(
                                 _kana.title_case(_kana.romanise(rd, st), particles=not is_person))
                             for st in ("macron", "double", "plain")}
        if rec.get("en"):
            # An "already Latin" title is detected by looking for kana and kanji, which means
            # IDOL×IDOL STORY！ passed as English with its full-width punctuation intact and then
            # short-circuited every later rendering. Punctuation is typography, not the name, so it
            # is normalised on the way out — the letters are untouched.
            # Sources hand back "HINO Arashi (日野アラシ)" — the original in brackets is their
            # convention for showing both, not part of the name, and it puts Japanese back on an
            # English page. Dropped when the bracketed part is entirely Japanese.
            _en = re.sub(r"\s*[（(][^)）]*[)）]\s*$", "",
                         rec["en"]) if re.search(r"[（(][ぁ-ヿ一-鿿\s]+[)）]\s*$", rec["en"]) else rec["en"]
            out["en"] = _p4.latinise(_en) if _p4 else _en
        if rec.get("basis"):
            out["basis"] = rec["basis"]
        # EVERY English form we hold, keyed by what makes it that form, so the reader can order
        # them. The store already keeps a displaced claim in en_conflicts rather than discarding
        # it, on the reasoning that a title somebody knows the work by is still worth finding;
        # shipping the map lets a reader who prefers a licensor's wording to the work's own say so,
        # which was previously a decision made here on their behalf.
        #
        # `romaji` is deliberately absent: it is not a claim about a name, it is the reading spelt
        # in Latin letters, and it is already shipped in three styles above.
        forms = {}
        for claim in [{"value": rec.get("en"), "basis": rec.get("basis")}] + list(
                rec.get("en_conflicts") or []):
            b, v = claim.get("basis"), claim.get("value")
            if v and b in ("official-jp", "licensed", "translated"):
                forms.setdefault(b, v)   # live claim first, so a superseded one cannot displace it
        if forms:
            out["en_forms"] = forms
        # HOW THE READING WAS ARRIVED AT, not merely whether to doubt it. The store distinguishes
        # a reading the source states, one taken from the kana surface, one a person researched and
        # wrote a note for, and one an analyser produced; all four shipped as a single boolean, so
        # a decision somebody made was displayed as indistinguishable from a machine's guess. That
        # is the same category error the English side avoids by naming licensed, official,
        # translated and romaji separately: a researched reading is an opinion, and an opinion with
        # a reason behind it is not a guess.
        if rec.get("reading_basis"):
            out["reading_basis"] = rec["reading_basis"]
        # False is meaningful and must survive; missing is not the same as verified.
        # A researched reading is exempt: somebody looked the word up and said why, which is
        # exactly what the mark is asking for, so marking it would ask for work already done.
        if rec.get("verified") is False and rec.get("reading_basis") not in ("researched",
                                                                             "stated"):
            out["unverified"] = True
        # A reading assembled character by character because nothing could read the word. Weaker
        # than an ordinary guess and marked separately: 抱き寝ーター came out カカエきネーター, where
        # 抱き is ダキ — the isolated reading of a character is often not its reading in a compound.
        if rec.get("reading_uncertain"):
            out["uncertain"] = True
        return out or None

    got = {}
    for kind in ("authors", "titles"):
        f = pathlib.Path("data/names") / f"{kind}.yaml"
        if not f.exists():
            got[kind] = {}
            continue
        d = (yaml.safe_load(f.read_text()) or {}).get("names") or {}
        got[kind] = {k: v for k, v in
                     ((k, render(k, v, is_person=(kind == "authors"))) for k, v in d.items()) if v}
    return got.get("authors", {}), got.get("titles", {})



def write_feed_split(out, releases, _today, platforms, plat_meta, lapsed,
                     contradicted_works, print_candidates, web_works, samples, regenerate=()):
    # ── The published feed, split ────────────────────────────────────────────────────────────────
    #
    # feed.json above is the INTERNAL whole — the acceptance tests and the audit sampler read it,
    # and it stays. What ships is this directory. One file of 1.3 MB was downloaded in full by every
    # visitor to render the first screen; at a year of accumulation that is unloadable, and the cost
    # falls hardest on the reader who only ever asks "what is new".
    #
    #   feed/current.json  — the rolling window the 更新 tab opens on.
    #   feed/YYYY-MM.json  — one completed month, fetched only if a reader asks for it.
    #   feed/meta.json     — everything that is NOT a release row.
    #
    # The month files carry `releases` and nothing else. platform_meta, lapsed, contradicted,
    # print_candidates and web_works are statements about the database as a whole, not about a
    # month, so repeating them in every archive would be both wrong and the very duplication this
    # split exists to remove. They go in meta.json once.
    CURRENT_WINDOW_DAYS = 14

    # Where the published archive stops going back, and why it is not simply "everything we hold".
    #
    # Update tracking began when this pipeline first ran. Everything dated before that was
    # bootstrap-imported in one pass from what each platform states about its own back catalogue —
    # real dates, mostly, but not a record of updates AS THEY HAPPENED: several platforms stamp a
    # whole back catalogue with the day they listed it (竹コミ gives 386 chapters one single day).
    # Publishing those months as "the updates of June 2026" would assert a history this project
    # never observed. They are not lost: they remain in series.json, which is what the 作品 tab is
    # built from and which is honest about being a chapter history rather than an update record.
    #
    # So the archive starts at the first month that is genuinely ours. Raise this only when there is
    # a month whose updates were actually watched happening.
    ARCHIVE_FROM_MONTH = "2026-07"

    feed_dir = out / "feed"
    feed_dir.mkdir(parents=True, exist_ok=True)

    def _fdate(r):
        return str(r.get("feed_date") or r.get("pub") or "")[:10]

    # The same identity the first-seen ledger uses. Not `id`: 11 of 1,366 rows share one, because a
    # release id is a platform's word for a chapter and two platforms can use the same word. This
    # key is what §5 locks a date against, so it is also what a divergence has to be reported in
    # terms of.
    def _row_key(r):
        return f"{norm_work(r.get('work') or '')}|{norm_work(r.get('ep') or '')}|" \
               f"{r.get('plat_name') or r.get('plat')}"

    # DAYS - 1, so the window is exactly CURRENT_WINDOW_DAYS calendar days counting today. Subtract
    # the full 14 and the tab shows fifteen date headings under a control that says "直近14日" —
    # a small lie, but the interface counting differently from its own label is the kind of thing
    # that makes a reader distrust the counts that matter.
    window_from = str(_today - datetime.timedelta(days=CURRENT_WINDOW_DAYS - 1))
    current_rows = [r for r in releases if _fdate(r) >= window_from]
    (feed_dir / "current.json").write_text(json.dumps(
        {"releases": current_rows,
         "window_days": CURRENT_WINDOW_DAYS, "from": window_from, "to": str(_today),
         "generated": str(_today)},
        ensure_ascii=False, indent=1, default=jsonable))

    # A month file holds the WHOLE month, including the days that also sit in the current window.
    # The alternative — "this month minus whatever the window still covers" — makes the file's
    # contents depend on the day the build ran, so a month written once would be frozen half
    # complete and the same month written a week later would disagree with it. A month is a month.
    by_month = defaultdict(list)
    for r in releases:
        d = _fdate(r)
        if len(d) >= 7:
            by_month[d[:7]].append(r)

    _archive_withheld = withheld_works()
    this_month = str(_today)[:7]
    # NOT `warnings` — that name already holds the works with no content_tier, collected at the
    # top of main(). Rebinding it here made the closing line report this block's warning count (0)
    # instead of 302 works awaiting human review, so real outstanding work silently read as done.
    archived, skipped_pre, archive_warnings = [], 0, []
    for m in sorted(by_month):
        if m < ARCHIVE_FROM_MONTH:
            skipped_pre += len(by_month[m])
            continue
        # The month in progress is not archived. It is not finished, so writing it would either
        # publish an incomplete month or require rewriting it tomorrow — and rewriting is the one
        # thing an archive may not do.
        if m >= this_month:
            continue
        path = feed_dir / f"{m}.json"
        payload = {"releases": by_month[m], "month": m, "generated": str(_today)}
        # WITHHELD BEATS WRITE-ONCE. §5's date locking protects a statement about DATES from being
        # quietly revised. It was never a licence to keep publishing a work that the adult-content
        # review has held back: an archive is still published, and a row nobody may see is a row
        # nobody may see whatever month it sits in. So a withheld work is removed from an existing
        # archive and the removal is stated, which is the opposite of quiet revision.
        if path.exists() and _archive_withheld:
            try:
                _old = json.loads(path.read_text()).get("releases") or []
            except (OSError, ValueError):
                _old = []
            _keep = [r for r in _old if norm_work(r.get("work")) not in _archive_withheld]
            if len(_keep) != len(_old):
                path.write_text(json.dumps({"releases": _keep, "month": m,
                                            "generated": str(_today)}, ensure_ascii=False))
                print(f"  archive {m}: removed {len(_old) - len(_keep)} withheld row(s); "
                      "§5 yields to the content register")
        if path.exists() and m in regenerate:
            # Deliberately overridden for this month. The rewrite is announced, and what changed is
            # counted, which is the opposite of the quiet revision §5 forbids.
            try:
                _was = len(json.loads(path.read_text()).get("releases") or [])
            except (OSError, ValueError):
                _was = 0
            # default=jsonable, like every other write here: a release carries date objects and
            # json.dumps refuses them.
            path.write_text(json.dumps(payload, ensure_ascii=False, default=jsonable))
            print(f"  archive {m}: REGENERATED on request, {_was} rows -> {len(by_month[m])}")
            archived.append((m, "regenerated", len(by_month[m])))
            continue
        if path.exists():
            # REQUIREMENTS §5, date locking. A published month is a statement about dates that has
            # already been made; a later run must not quietly revise it. So it is never rewritten —
            # instead any difference is named here, loudly, where it can be looked at. A divergence
            # is detectable at all because first-seen.yaml keys a release by (work, episode,
            # platform) and remembers when we first saw it, so "the same row, dated differently"
            # can be told apart from "a different row".
            try:
                old = json.loads(path.read_text()).get("releases") or []
            except (OSError, ValueError) as e:
                archive_warnings.append(f"feed/{m}.json exists but could not be read ({e}) — left alone")
                archived.append((m, "unreadable", 0))
                continue
            o = {_row_key(r): r for r in old}
            n = {_row_key(r): r for r in by_month[m]}
            diffs = []
            for k in sorted(set(o) | set(n)):
                if k not in o:
                    diffs.append(f"    + not in the published month: {k}  ({_fdate(n[k])})")
                elif k not in n:
                    diffs.append(f"    - published but no longer built: {k}  ({_fdate(o[k])})")
                else:
                    changed = [f for f in ("pub", "feed_date", "url", "ep", "kind", "free", "type")
                               if o[k].get(f) != n[k].get(f)]
                    if changed:
                        diffs.append(f"    ~ {k}: " + ", ".join(
                            f"{f} {o[k].get(f)!r} -> {n[k].get(f)!r}" for f in changed))
            if diffs:
                archive_warnings.append(
                    f"feed/{m}.json is already published and was NOT rewritten; "
                    f"{len(diffs)} row(s) differ from what this run would have written:\n"
                    + "\n".join(diffs[:40])
                    + (f"\n    … and {len(diffs) - 40} more" if len(diffs) > 40 else ""))
            archived.append((m, "kept", len(old)))
        else:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=jsonable))
            archived.append((m, "written", len(by_month[m])))

    (feed_dir / "meta.json").write_text(json.dumps(
        {"platforms": platforms,
         # Works a comparator reports as updating that the platform's own full chapter history
         # contradicts. Recorded rather than silently dropped: they are not coverage we lack.
         "contradicted": contradicted_works,
         "print_candidates": print_candidates, "web_works": web_works,
         "samples_dropped": len(samples),
         "platform_meta": plat_meta, "lapsed": lapsed,
         # Newest first: the interface offers these as "earlier updates", and the most recent
         # month is the one most likely to be wanted.
         "archive_months": [m for m, _s, _n in sorted(archived, reverse=True)],
         "archive_from": ARCHIVE_FROM_MONTH,
         "window_days": CURRENT_WINDOW_DAYS,
         "generated": str(_today)},
        ensure_ascii=False, indent=1, default=jsonable))

    print(f"feed split      : current {len(current_rows)} rows "
          f"({window_from}..{_today}, {CURRENT_WINDOW_DAYS}d)"
          f" · archives " + (", ".join(f"{m} {n} {s}" for m, s, n in archived) or "none")
          + (f" · {skipped_pre} rows before {ARCHIVE_FROM_MONTH} not published as archives "
             f"(bootstrap-imported back catalogue; they stay in series.json)" if skipped_pre else ""))
    for w in archive_warnings:
        print(f"  !! {w}")



def write_run_record(out, _today, releases, platforms, works, series_rows,
                     claim_trace, dropped_dupes, thin_dropped, resolver_dropped,
                     filled_author, filled_access, samples, catalogue_rows=()):
    # ── The run record ───────────────────────────────────────────────────────────────────────────
    #
    # build.py has always printed its counts to stdout and kept none of them, so nothing could say
    # what last night's run did or what broke. That gap is also why a claim could not be refuted
    # safely: "the platform lists nothing" and "our fetch of that platform failed" are the same
    # observation from inside the build unless the run says which happened. So the per-source
    # freshness below is not decoration — it is the evidence a refutation rests on.
    src_health = []
    for d0 in sorted(glob.glob("data/source/*/")):
        name = pathlib.Path(d0).name
        files = sorted(glob.glob(d0 + "*.yaml"))
        if not files:
            continue
        got, retrieved, works_n = 0, "", 0
        for f in files:
            try:
                y = yaml.safe_load(open(f)) or {}
            except Exception:
                continue
            r0 = str(y.get("retrieved") or "")[:10]
            retrieved = max(retrieved, r0)
            # Two file shapes. Platform adapters write one file holding many works; the
            # bibliographic sources (MADB, openBD, NDL) write one file PER WORK, with the work at
            # the top level. Counting only `works:` reported those as zero, which on a health panel
            # reads as a broken adapter rather than a different layout.
            ws = y.get("works") or y.get("releases")
            if ws is None:
                ws = [y] if y.get("record_type") else []
            works_n += len(ws)
            got += sum(len(w.get("chapters") or w.get("episodes") or w.get("volumes") or []) or 1
                       for w in ws if isinstance(w, dict))
        age = None
        if retrieved:
            try:
                age = (_today - datetime.date.fromisoformat(retrieved)).days
            except ValueError:
                pass
        src_health.append({"source": name, "files": len(files), "works": works_n,
                           "rows": got, "retrieved": retrieved, "age_days": age,
                           "in_scope": name in ALLOWED_SOURCES or name in
                           {"gigaviewer", "comicfuz", "kadokomi", "comici", "webpages",
                            "remaining", "render", "sitemap", "reachable", "comparators"},
                           "empty": works_n == 0})

    # ── Releases per week, and what precedes the record ──────────────────────────────────────────
    #
    # status.html drew this itself out of feed.json. It cannot any more: the published feed is a
    # 14-day window plus month archives, and pointing a whole-history graph at the archives would
    # mean downloading every month to draw one picture — reintroducing the 1.3 MB the split exists
    # to remove, on the page that is least often opened. The histogram is small, so the build
    # computes it once and run.json carries it.
    #
    # Publication dates, NOT run history. The distinction matters: no run before today was ever
    # recorded, so a "changes per run" graph would have to invent its own past. This is made only of
    # dates the platforms themselves stated.
    wk = Counter()
    for r in releases:
        p = str(r.get("pub") or "")[:10]
        if not re.fullmatch(r"\d{4}-\d\d-\d\d", p):
            continue
        d0 = datetime.date.fromisoformat(p)
        wk[str(d0 - datetime.timedelta(days=(d0.weekday() + 1) % 7))] += 1   # week beginning Sunday
    keys = sorted(wk)[-26:]
    # Trim the leading window edge, exactly as the page used to. The source layer holds a rolling
    # ~60 days, so weeks older than that appear only where something was discovered late — two or
    # three rows against a typical two hundred. Drawn as bars they read as a collapse in publishing,
    # which is the opposite of what happened: those weeks are thin in OUR record, not in the world.
    # A bar chart cannot caption itself, so the underpopulated tail comes off rather than being
    # explained away underneath.
    _med = (sorted(wk.values())[len(keys) // 2] if wk else 0)
    trimmed = 0
    while len(keys) > 4 and wk[keys[0]] < _med * 0.25:
        keys = keys[1:]
        trimmed += 1

    # The count of releases predating the first retrieval, for the "when the record starts" note.
    # Same reason as the histogram: status.html worked it out of feed.json and no longer can.
    _from = sorted(s["retrieved"] for s in src_health if s.get("retrieved"))
    _from = _from[0] if _from else None
    pre_tracking = sum(1 for r in releases if str(r.get("pub") or "") < _from) if _from else 0

    # ── Bulk re-dating ───────────────────────────────────────────────────────────────────────
    # Platforms periodically stamp a run of chapters with one timestamp. Verified against the
    # publisher: ichicomi.com answers "publishedAt":"2026-06-05T02:00:00Z" for chapter 1 AND
    # chapter 12 of the same twelve-chapter serial. It is not a platform that fails to record
    # dates — 一迅プラス has 74 distinct dates across 197 works — and the cause is not always a
    # migration; it also happens to ordinary runs for no reason visible from outside.
    #
    # Detected by comparing each (platform, date) bucket against that platform's own median day, so
    # it needs no per-platform configuration and catches new cases without anyone noticing them
    # first. This is a DIAGNOSTIC: it is recorded here and shown on the technical view, and it does
    # not alter a single date. The dates are the platform's own statement and the chapter genuinely
    # became available then — they are simply not per-chapter publication dates, which is what the
    # standing note in the interface already tells readers.
    #
    # distinct_works is the part worth reading. 123 rows across ONE work is a back catalogue
    # arriving at once; 277 rows across 16 works is a platform-wide restamp. Same shape, different
    # events, and a bare row count cannot tell them apart.
    _by_pd, _per_plat = Counter(), {}
    for r in releases:
        pn = r.get("plat_name") or r.get("plat")
        if pn and r.get("pub"):
            _by_pd[(pn, r["pub"][:10])] += 1
    for (pn, _d), n in _by_pd.items():
        _per_plat.setdefault(pn, []).append(n)
    bulk = []
    for (pn, d0), n in sorted(_by_pd.items(), key=lambda x: -x[1]):
        med = statistics.median(_per_plat[pn])
        if n >= max(20, med * 12):
            # NOT `works` — that name is already the compiled bibliographic list in this scope,
            # and rebinding it here turned 302 dicts into a set of title strings 30 lines later.
            bulk_works = {r["work"] for r in releases
                          if (r.get("plat_name") or r.get("plat")) == pn and r["pub"][:10] == d0}
            bulk.append({"platform": pn, "date": d0, "releases": n,
                         "distinct_works": len(bulk_works), "median_per_day": med,
                         "example_work": sorted(bulk_works)[0] if bulk_works else None})
    if bulk:
        _s = ", ".join(f"{b['platform']} {b['date']} x{b['releases']}" for b in bulk[:4])
        print(f"bulk re-dating  : {len(bulk)} (platform, date) bucket(s) far above that "
              f"platform's own median — {_s}")

    # run.json and meta.json are DEPLOYED, so a withheld work's title must not survive in a claim
    # trace or a coverage list either. Six published surfaces carried these titles in all; each was
    # checked separately because removing them from the first three looked like it had worked.
    _wh = withheld_works()
    claim_trace = [t for t in claim_trace if norm_work(t.get("work")) not in _wh]

    # Every content flag, reported whether or not it withholds anything. This is the whole remedy
    # for a register nothing read: the flags now have to appear in a published number, and check.py
    # fails if one exists that nothing accounts for.
    _flags = {**content_flags(), **marketing_flags(series_rows)}
    _published = {norm_work(r["work"]) for r in series_rows}
    content_flag_rows = sorted(
        ({"title": v["title"], "source": v["source"], "reason": v["reason"],
          "withheld": v["withhold"], "published": (k in _published) and not v["withhold"]}
         for k, v in _flags.items()), key=lambda r: r["title"])

    cl = Counter(t["disposition"] for t in claim_trace)
    (out / "run.json").write_text(json.dumps(
        {"generated": str(_today),
         "releases": len(releases), "platforms": len(platforms),
         "works": len(works), "series_rows": len(series_rows),
         "sources": src_health,
         # Claims never reach the reader. They are inputs, and this is where they end up.
         "claims": {"total": len(claim_trace), "by_disposition": dict(cl), "trace": claim_trace},
         # Named in full rather than counted, because a number alone cannot be reviewed and the
         # point of this block is that somebody can look at what was flagged.
         "content_flags": {"total": len(content_flag_rows),
                           "withheld": sum(1 for r in content_flag_rows if r["withheld"]),
                           "published": sum(1 for r in content_flag_rows if r["published"]),
                           "rows": content_flag_rows},
         "bulk_dated": bulk,
         # Cases the reader-facing interface used to render as doubt, now decided and moved here.
         # A work with no chapters at all is a lead; a volume grouped by title match rather than an
         # explicit series link is our inference. Neither is something a reader can adjudicate, and
         # both are real coverage facts, so they are counted where the coverage facts live.
         "gaps": {
             "uncaptured_works": [
                 {"work": r["work"],
                  "platform": (r.get("sources") or [{}])[0].get("platform")}
                 for r in series_rows if not r.get("chapters")],
             "grouping": dict(Counter(w.get("grouping") or "unknown" for w in works)),
             # Set aside, and counted, because setting things aside is how a number quietly
             # becomes a way of losing them. These are カドコミ shop entries for works it does not
             # serialise: the volumes are for sale, nothing was ever published there to read, and
             # they were sitting in the web list as work somebody might go and do.
             "catalogue_listings": [
                 {"work": r["work"], "why": r.get("set_aside"),
                  "platform": (r.get("sources") or [{}])[0].get("platform")}
                 for r in catalogue_rows],
         },
         # Weeks already trimmed and ready to draw; `trimmed_weeks` says how many came off, so the
         # page can be honest about the window without recomputing anything.
         "weekly": {"weeks": [{"week": k, "n": wk[k]} for k in keys],
                    "trimmed_weeks": trimmed, "pre_tracking_releases": pre_tracking,
                    "tracking_from": _from},
         "access_modes": dict(Counter(m for r in releases for m in (r.get("access_modes") or []))),
         "update_kinds": dict(Counter(r.get("kind") for r in releases)),
         "identification": dict(Counter(r.get("ident") for r in releases)),
         "collapsed": {"duplicate_chapters": dropped_dupes, "thin_sitemap": thin_dropped,
                       "resolver": resolver_dropped, "samples": len(samples)},
         "filled": {"author": filled_author, "access": filled_access}},
        ensure_ascii=False, indent=1, default=jsonable))
    print(f"claims traced   : {dict(cl)}")
    return cl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/build")
    # REGENERATING AN ARCHIVE OVERRIDES §5, which is why it takes a deliberate flag naming the
    # month rather than happening because a file was deleted. Date locking exists so that a
    # published month cannot be quietly revised; correcting a classification is not a revision of
    # its dates, but it IS a rewrite, and a rewrite should be an act somebody performed and can be
    # found in the shell history rather than a side effect.
    ap.add_argument("--regenerate-archive", metavar="YYYY-MM", action="append", default=[],
                    help="rewrite an already-published month. Overrides the write-once rule; "
                         "use when a classification fix must reach an archived month.")
    a = ap.parse_args()
    # Held under a name nothing else uses. `a` is rebound further down main() as a loop variable,
    # so reading a.regenerate_archive at the end of a 2,900-line function got whatever `a` last
    # happened to be, which was None. This is the shape adapters/lint/shadowing.py counts, met in
    # the wild about ten minutes after being written about.
    ARGS = a

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
    platform_history = load_platform_history(
        glob.glob("data/source/gigaviewer/*-series-feeds.yaml")
        + glob.glob("data/source/gigaviewer/*-confirmed.yaml")
        + glob.glob("data/source/comicfuz/works.yaml")
        # The comici and rendered-page adapters write here, in the same shape. Omitting them left
        # 28 of 43 claims reported as untraced while their chapter lists sat on disk, one of them
        # in a file called claim-resolved.yaml. Fetched, written, and read by nothing.
        + glob.glob("data/source/webpages/*.yaml"))

    # WHAT EACH PLATFORM SAYS ABOUT ITS OWN RHYTHM. GigaViewer prints a work's cadence and its
    # next update date, and we were inferring both from gaps between the chapters we happened to
    # capture. See adapters/render/schedule_text.py for why that was not merely redundant.
    stated_schedule = {}
    _owners = host_platforms(
        (yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text()) or {}).get("platforms", []))
    for _sf in (glob.glob("data/source/webpages/rendered-*.yaml")
                + ["data/source/kadokomi/chapters.yaml",
                   "data/source/webpages/ganganonline.yaml"]):
        if not pathlib.Path(_sf).exists():
            continue
        _sd = yaml.safe_load(open(_sf)) or {}
        _spn = _sd.get("platform_name") or ""
        for _sw in _sd.get("works") or []:
            if not _sw.get("stated_schedule"):
                continue
            # Same rule as the histories: the platform is the host we read, and only the file's
            # own label where the URL cannot say. カドコミ's file names no platform at all.
            _p = platform_of(_sw.get("url"), _owners) or _sw.get("platform_name") or _spn
            stated_schedule[(norm_work(_sw.get("work_title") or ""), norm_work(_p))] = \
                _sw["stated_schedule"]
    _STATED.update(stated_schedule)

    # WHAT THE ANTENNA SAYS HAS FINISHED. A claim rather than an attestation, and the only
    # completion signal that reaches most platforms: probing one dormant work on each of ten
    # platforms found the platform itself marking completion on two. Weighed below against how long
    # the work has actually been silent, because a lead plus a long silence is evidence where
    # either alone is not.
    # A PERSON LOOKED AND WROTE DOWN WHICH PAGE. Ranked above the antenna's tag, which is a lead
    # under DEFINITIONS §5, because a cited publisher page is not. See adapters/completion.py.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
    import completion as _comp
    reviewed = {norm_work(w): e for w, e in _comp.verdicts().items()}

    completion_claims = {}
    _cc = pathlib.Path("data/source/comparators/completion.yaml")
    if _cc.exists():
        for _c in (yaml.safe_load(_cc.read_text()) or {}).get("claims") or []:
            completion_claims[norm_work(_c.get("work") or "")] = _c.get("seen")

    # A licensed shop stating the series is finished. Ranked above the antenna's tag, because
    # BOOK☆WALKER sells the publisher's edition and describes its own stock, where an aggregator
    # infers from what stopped appearing. It settles works no platform will speak about, and it
    # corrects inference: こはる日和。 and すわっぷ⇔すわっぷ both stopped printing years before
    # their last chapter, which read as a print edition ending under a story that continued. The
    # shop says both are finished, and an explicit statement beats a shape in the data.
    # Both passes, because the question is the same one and only the queue differed: the first
    # asked about works that had gone quiet, the second about works merely slowing down, and a
    # shop saying 完結 answers either. Ten of the 94 slow works carry it.
    shop_completed = {}
    for _bwf in ("data/coverage/bookwalker-completion.yaml",
                 "data/coverage/bookwalker-completion-slow.yaml"):
        _bw = pathlib.Path(_bwf)
        if _bw.exists():
            for _c in (yaml.safe_load(_bw.read_text()) or {}).get("works") or []:
                shop_completed[norm_work(_c.get("work") or "")] = _c

    # WHAT A PLATFORM SAYS ITS OWN SERIES IS LONG, where it says it and we hold less. Neither file
    # carries titles or dates, so neither can fill in the chapters we lack. What they stop is a
    # partial capture being published as a whole series: ベイビー車中ハッカーズ read "2 chapters,
    # complete, dormant since October 2024" about a work at its nineteenth instalment.
    stated_len = {}
    for _lf in ("data/coverage/series-lengths.yaml", "data/coverage/magapoke-lengths.yaml"):
        _lp = pathlib.Path(_lf)
        if not _lp.exists():
            continue
        for _w in (yaml.safe_load(_lp.read_text()) or {}).get("works") or []:
            _len_key = norm_work(_w.get("work") or _w.get("work_title") or "")
            _len_n = _w.get("episodes_stated")
            if _len_key and _len_n:
                stated_len[_len_key] = {"n": _len_n, "url": _w.get("url"),
                                  "holds_last": _w.get("holds_last"),
                                  "last_episode_url": _w.get("last_episode_url")}

    # Every look adapters/claims/trace.py has taken, keyed the way it writes them. A claim with no
    # history behind it is untraced only if nobody has been; this is how that is known.
    claim_checks = checkstate.load()

    # Platforms that carry other people's serialisations and publish no index of their own. A claim
    # naming one, with no URL, has nothing behind it to fetch.
    carrier_platforms = {norm_work(x["name"]) for x in
                         (yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text()) or {})
                         .get("platforms", []) if x.get("syndicated")}

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

    # ── Claims are traced, not published ─────────────────────────────────────────────────────────
    #
    # A claim is a listing site saying a work updated. It is an input to this pipeline, not an
    # output of it. Earlier versions put unconfirmed claims into the feed marked 要確認, which is a
    # category error: nothing but this system will ever check them, so asking a reader to hold an
    # open question serves no one — they cannot act on it and it is not a fact about a manga.
    #
    # Every claim therefore ends in exactly one disposition, and the ones a reader would want are
    # already indistinguishable from attested rows because they ARE attested rows (absorbed). The
    # rest go to the technical view: `open` is a worklist, `refuted` is a record kept in case it
    # ever needs revisiting, and the others are dead ends with a stated reason.
    #
    #   absorbed    the platform attests it too. Ceases to be a claim; the release stands on its own
    #   phantom     the "work" is not a work (a section heading, a magazine name)
    #   duplicate   the other comparator reported the same event
    #   refuted     we hold the platform's own history, it is deep enough to argue from, and it
    #               contains nothing near the claimed date. We looked at the publisher. That is the
    #               end — UNLESS the capture guards below fail, in which case it stays `open`.
    #   undatable   the platform publishes no per-chapter dates at all, so its pages can neither
    #               confirm nor refute. Not neglect; there is nothing there to read.
    #   open        not traced yet. This is work to do now, and it is the only bucket that should
    #               ever shrink by doing something.
    #
    # THE CAPTURE GUARDS exist because "we found nothing" and "we fetched nothing" look identical
    # from inside. A refutation is only allowed when our own capture is deep enough to carry it:
    # three chapters minimum (a history of one is not a history), and no huge gap between the claim
    # and our newest (a large gap is the signature of a partial listing — pixivコミック expires its
    # middle chapters, several GigaViewer installs serve only what is currently free). Every
    # refutation records the evidence that licensed it, so the "we just failed to capture it"
    # hypothesis stays visible on the technical screen instead of being assumed away.
    claim_trace = []
    # WORKS THAT ALSO RUN IN PRINT. A web platform's chapter dates cannot refute a claim about one
    # of these, because the two record different events: コミック百合姫 prints an instalment and
    # 一迅プラス puts it online weeks later. Sixteen of nineteen refutations were 一迅プラス and eleven
    # were works on a 百合姫 imprint in our own catalogue; the gaps clustered at magazine intervals
    # — 14, 28, 31, 35, 36 days — and several were NEGATIVE, the web chapter arriving after the
    # claim rather than before it.
    #
    # REQUIREMENTS §4 already had this: absence is evidence of absence only where the list is known
    # to be complete. A publisher's web arm is not a complete list of that publisher's output.
    #
    # Read from data/source/madb directly rather than from `works`, which is compiled hundreds of
    # lines below this and would not exist yet.
    publisher_platforms = {norm_work(x["name"]) for x in
                           (yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text()) or {})
                           .get("platforms") or [] if x.get("publisher")}

    print_serialised = set()
    for _f in glob.glob("data/source/madb/*.yaml"):
        try:
            _d = yaml.safe_load(open(_f)) or {}
        except Exception:
            continue
        _t = _d.get("title")
        _t = _t.get("ja") if isinstance(_t, dict) else _t
        if _t:
            print_serialised.add(norm_work(_t))

    contradicted, contradicted_works = 0, []
    CLAIM_DATE_SLACK = 2   # days either side

    def trace(c, w, disposition, why, **ev):
        """Record one claim's outcome, and index it so a duplicate of it can be recognised.

        THE INDEX USED TO BE FILLED IN ONE PLACE ONLY, at the foot of the untraced branch, so a
        claim that was absorbed or refuted earlier never entered it. 百合ナビ runs the author into
        the title cell and supplies no URL, so its row for a work is a near-duplicate of
        webcomics.jp's, and the dedupe below could only see the duplicates of claims nothing had
        settled. 君のせいなんだった、責任とってよね。 was traced from webcomics.jp with a URL and
        then reported a second time, from 百合ナビ, as untraced work.
        """
        rec = {"work": w, "platform": c.get("platform"), "url": c.get("url"),
               "claimed": str(c.get("date") or ""), "source": c.get("source"),
               "disposition": disposition, "why": why, **ev}
        claim_trace.append(rec)
        claim_index.setdefault(str(c.get("date") or ""), []).append(
            {"nw": norm_work(w or ""), "rec": rec})

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
        # CLAIMS THAT NAME A PAGE ARE TRACED FIRST. Two comparators report the same update, and
        # the dedupe below keeps whichever arrived first and folds the second into it. 百合ナビ
        # runs the author into the title cell and gives no URL, and its rows happen to come first
        # in the file, so the record kept was the one with nothing to trace to while the row
        # carrying the link was merged away into it. Ordering is not a tie-break here: it decides
        # which of two reports of one event the system is left holding.
        # A URL WE ALREADY HOLD. 百合ナビ reports a work with no link and runs the author into the
        # title cell, and a previous pass resolved several of those to a page by searching the
        # carrying platform's own domain. That file is read three times elsewhere in this build and
        # was never consulted here, so a claim sat reported as untraceable while the address it
        # needed was on disk. Matched on the cell, which is "<title> <author>", against the two
        # fields the resolution recorded separately.
        _resolved = {}
        _rtf = pathlib.Path("data/source/comparators/resolved-titles.yaml")
        if _rtf.exists():
            for _r in (yaml.safe_load(_rtf.read_text()) or {}).get("works") or []:
                if _r.get("url"):
                    _resolved[(norm_work(f"{_r.get('title','')} {_r.get('author','')}"),
                               norm_work(_r.get("platform") or ""))] = _r["url"]
                    _resolved[(norm_work(_r.get("title") or ""),
                               norm_work(_r.get("platform") or ""))] = _r["url"]

        for c in sorted(d.get("updates") or [], key=lambda x: (not x.get("url"))):
            if not c.get("url"):
                c = dict(c)
                c["url"] = _resolved.get((norm_work(c.get("work") or ""),
                                          norm_work(c.get("platform") or "")))
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
                trace(c, w, "phantom", "the name is not a work")
                continue
            if (nw, when) in attested_keys:
                trace(c, w, "absorbed", "the platform attests this work on this date")
                continue
            # Comparators and platforms disagree by a day or two routinely — a listing site records
            # when it noticed, the platform when it published, and timezones and crawl schedules do
            # the rest. 白き乙女の人狼 is attested on 竹コミ for 2026-07-10 and claimed for 07-12.
            # Treating those as two events shows the reader one update twice, the second time
            # marked unconfirmed. Exact-date matching was too strict for what these dates are.
            if any((nw, d) in attested_keys for d in near_dates(when)):
                claims_superseded_nearby += 1
                trace(c, w, "absorbed",
                      f"attested within {CLAIM_DATE_SLACK} days — the same event, dated differently")
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
                trace(c, w, "absorbed", "attested on this platform within a week — one event",
                      platform_latest=max(same_plat))
                continue
            # 百合ナビ runs title and author together in one cell, so an exact-key test misses a
            # claim that duplicates an attested release — "リリィズコンプレックス 館山けーた" against
            # "リリィズコンプレックス". Suppress a claim whose cell starts with a title we already
            # attest on that date.
            if any(nw.startswith(k) for k, kd in attested_keys if kd == when and len(k) >= 2):
                trace(c, w, "absorbed", "attested on this date; the cell runs title and author together")
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
            raw_hist = platform_history.get((nw, norm_work(c.get("platform") or "")))
            plat_hist, held_back = raw_hist, None
            if raw_hist:
                gap = (datetime.date.fromisoformat(when)
                       - datetime.date.fromisoformat(max(raw_hist))).days
                if gap > CONTRADICTION_MAX_GAP:
                    plat_hist, held_back = None, (
                        f"we hold {len(raw_hist)} chapters ending {max(raw_hist)}, {gap} days before "
                        f"the claim — too far behind to argue the platform shows nothing")
                elif len(raw_hist) < 3:
                    plat_hist, held_back = None, (
                        f"only {len(raw_hist)} chapter(s) held — a history of one is not a history")
            # THE PLATFORM, NOT JUST THE WORK. Matching against MADB only catches serialisations
            # already collected into volumes — a running one is not there yet, which is why eight
            # claims survived the first version of this rule with gaps of exactly the same
            # magazine shape (14, 11, 31, -14, -28). The completeness problem is a property of the
            # PLATFORM: 一迅プラス, コミックDAYS, webアクション and サンデーうぇぶり are publishers' web
            # arms, and a publisher's web arm is not a complete list of that publisher's output.
            # data/platforms.yaml already records which platforms have a publisher.
            would_refute = (plat_hist and not any(
                abs((datetime.date.fromisoformat(when)
                     - datetime.date.fromisoformat(x)).days) <= 7 for x in plat_hist))
            # Only where we WOULD have refuted. A claim on a publisher's platform for a work we
            # hold no history of is genuinely untraced, and calling it print-serialised would
            # assert a magazine origin we have not established — trading one unfounded disposition
            # for another.
            if would_refute and (nw in print_serialised
                                 or norm_work(pn_claim) in publisher_platforms):
                # Not refuted and not merely untraced: the claim is about a magazine instalment and
                # the platform we hold cannot speak to it either way.
                trace(c, w, "print-serialised",
                      "a magazine-dated claim cannot be confirmed or refuted by a publisher's web "
                      "arm — the two record different events, and the web chapter typically "
                      "follows the print instalment by two to five weeks",
                      platform_latest=max(plat_hist) if plat_hist else None)
                continue
            if plat_hist and not any(abs((datetime.date.fromisoformat(when)
                                          - datetime.date.fromisoformat(x)).days) <= 7
                                     for x in plat_hist):
                contradicted += 1
                ev = {"work": w, "platform": c.get("platform"), "claimed": when,
                      "platform_latest": max(plat_hist),
                      "chapters_held": len(plat_hist), "source": c.get("source")}
                contradicted_works.append(ev)
                trace(c, w, "refuted",
                      "we hold this platform's own history for this work and it lists nothing "
                      "within a week of the claimed date",
                      platform_latest=max(plat_hist), chapters_held=len(plat_hist),
                      gap_days=(datetime.date.fromisoformat(when)
                                - datetime.date.fromisoformat(max(plat_hist))).days)
                continue

            # The two comparators overlap, and 百合ナビ's cell carries the author, so the same
            # update arrives twice under different strings. Keep the first and record that both
            # reported it, rather than showing the reader one event twice.
            dup = next((c2 for c2 in claim_index.get(when, [])
                        if nw.startswith(c2["nw"]) or c2["nw"].startswith(nw)), None)
            if dup:
                srcs = set((dup["rec"].get("source") or "").split("+")) | {c.get("source")}
                dup["rec"]["source"] = "+".join(sorted(s for s in srcs if s))
                continue
            # Everything left is untraced. Say WHY it is untraced, because the reasons need
            # different work: a platform that dates nothing can never be resolved and should stop
            # being retried, while a platform we simply do not read yet is an adapter waiting to be
            # written, and a work whose history we hold too thinly is a deeper fetch.
            if norm_work(c.get("platform") or "") in dateless_platforms:
                trace(c, w, "undatable",
                      "this platform publishes no per-chapter dates — a reader on the site cannot "
                      "see when a chapter appeared either, so there is nothing to check against")
            else:
                # LOOKED AT, AND STILL UNSETTLED, is not the same as NOT LOOKED AT, and the status
                # page was reporting the first as the second. `open` says "not yet traced. This is
                # the work outstanding", which asks somebody to go and do a thing that has already
                # been done and cannot be finished: where a platform's own listing is partial, or
                # too far behind, or simply empty, its silence proves nothing however often it is
                # read. That is a terminal state, and parking it in a queue is the same category
                # error as 要確認, a permanent condition wearing the clothes of pending work.
                #
                # The two are told apart by the check ledger rather than by the history, because
                # both leave the same absence behind. adapters/claims/trace.py records every look.
                looked = claim_checks.get(f"{c.get('platform') or ''}|{w}") or {}
                sched = stated_schedule.get((nw, norm_work(c.get("platform") or ""))) or {}
                # THE PLATFORM'S OWN SCHEDULE PUTS AN UPDATE HERE. 平良深姉妹はどっちもヤんでる
                # states 毎月第3金曜 and announces a next update; 2026-07-17 is a third Friday, so
                # the report matches what the platform says it does. That is corroboration from the
                # platform and it is not attestation of a chapter, so it gets its own disposition
                # rather than being called absorbed: no row exists for it in the database.
                if _sched_fits(sched.get("cadence"), when):
                    trace(c, w, "scheduled",
                          f"the platform states it updates {sched['cadence']} and this date falls "
                          f"where that puts one"
                          + (f"; it announces the next for {sched['next_update']}"
                             if sched.get("next_update") else ""),
                          cadence=sched.get("cadence"), next_update=sched.get("next_update"))
                elif held_back:
                    # The cadence rides along even where it does not decide. A gap of 419 days
                    # reads as a dead series until the same page says the work updates monthly and
                    # names the next date, at which point it plainly reads as our sample of a
                    # rolling free window.
                    trace(c, w, "unsettleable",
                          held_back + (f"; the platform states it updates {sched['cadence']}"
                                       if sched.get("cadence") else ""),
                          chapters_held=len(raw_hist or []), last_looked=looked.get("last_checked"),
                          cadence=sched.get("cadence"), next_update=sched.get("next_update"))
                # `error` is left out on purpose: a timeout or a 5xx may pass, and a claim behind
                # one is still worth another look. The rest are standing conditions: we read the
                # listing, or the platform will not show it to us, and no number of retries changes
                # either of those.
                elif looked.get("result") in ("empty", "ok", "blocked", "missing"):
                    trace(c, w, "unsettleable",
                          looked.get("note")
                          or "we read this platform's own listing and it carries nothing dated here",
                          chapters_held=0, last_looked=looked.get("last_checked"))
                elif not c.get("url") and norm_work(c.get("platform") or "") in carrier_platforms:
                    # A CARRIER, not a publisher. きららベース shows works serialised elsewhere and
                    # publishes no index, sitemap or usable search, which data/platforms.yaml has
                    # recorded since it was surveyed: each of its works has to be resolved one at a
                    # time by external search. With no URL reported and none held, there is no page
                    # to address, and that is a standing condition rather than a queue.
                    trace(c, w, "unsettleable",
                          "no URL reported, and this platform carries works published elsewhere "
                          "without an index we can enumerate, so there is no page to address",
                          chapters_held=0)
                else:
                    trace(c, w, "open",
                          ("we hold no chapter history for this work on this platform"
                           if c.get("url") else
                           "no URL reported, and no history held — nothing to trace to"),
                          chapters_held=len(raw_hist or []),
                          also_attested_elsewhere=nw in attested_works,
                          traceable=bool(c.get("url")),
                          last_looked=looked.get("last_checked"),
                          blocked=looked.get("note"))
            # (indexed by trace() itself, for every disposition)
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
        # Before the generic notice rule, because a skipped slot is a more specific and more useful
        # fact than "notice": it is dated, publisher-attested, and says the schedule was kept while
        # the chapter was not.
        if is_skipped_slot(ep):
            r["kind"] = "skipped"
            r["kind_basis"] = "the publisher posted a hiatus notice in this release slot"
            continue
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
        # Before the numbering. A prize citation carries a number that is not a chapter number, and
        # a competition entry is one instalment: the piece that was entered.
        if is_prize_entry(ep) and not has_earlier:
            r["kind"], r["kind_basis"] = "oneshot", "published as a competition entry"
            r["kind_inferred"] = True
            continue
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
        elif n is not None and (has_earlier or count.get(norm_work(r["work"]), 0) > 1):
            r["kind"], r["kind_basis"] = "new-chapter", f"episode numbered {n}"
        elif n is not None:
            # A number without an earlier chapter to be later THAN. This is the first sighting of a
            # work that was already running, so it is neither a start nor a demonstrable
            # continuation, and saying "new chapter" asserts a history we do not hold. The number
            # is reported instead, which is the fact we actually have.
            r["kind"] = "new-chapter"
            r["kind_basis"] = (f"numbered {n}, but this is the only chapter we hold: the work was "
                               f"already running when we first saw it")
            r["kind_inferred"] = True
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
    # Withheld before anything else. A work awaiting the adult-content review must not reach the
    # feed, the works list or the counts, so it is dropped at the same point 試し読み is, and for
    # the same reason: a hidden row still inflates totals.
    _withheld = withheld_works()
    if _withheld:
        _dropped = [r for r in releases if norm_work(r.get("work")) in _withheld]
        releases = [r for r in releases if norm_work(r.get("work")) not in _withheld]
        if _dropped:
            print(f"withheld            : {len(_dropped)} release(s) across "
                  f"{len({r['work'] for r in _dropped})} work(s) held back pending review")

    # A 試し読み instalment is a preview of a printed collection, not web publication (§6). The
    # anthology split further down names its work and author, which is right and stays, but it runs
    # AFTER this drop, so marking the web status there left every preview in the feed regardless.
    # The status is set here, where the thing that consumes it can see it.
    _prev = 0
    for r in releases:
        if str(r.get("ep") or "").strip().startswith("【試し読み") and r.get("web") != "promotional-sample-only":
            r["web"] = "promotional-sample-only"
            _prev += 1
    if _prev:
        print(f"previews            : {_prev} 試し読み instalment(s) held out of the feed as "
              "promotional samples")

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
    # meta.json is deployed, so a withheld work must not survive here either. Skipped before the
    # field checks below, or a work nobody may publish still raises errors about its labelling.
    _wh_web = withheld_works()
    for f in sorted(glob.glob("data/source/kadokomi/confirmed.yaml")):
        d = yaml.safe_load(open(f)) or {}
        for w in d.get("works") or []:
            if norm_work(w.get("work_title")) in _wh_web:
                continue
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
    COLLECTION = re.compile(r"アンソロジー|短編集|読切シリーズ|読み切りシリーズ|読切集|オムニバス|傑作選")
    # An instalment that names its own author and title IS A WORK, and is recorded as one. It does
    # not fit the model cleanly — it has no series id of its own, its URL belongs to the container,
    # and its "platform" is the container's platform — but a 読切 by 白玉もち called 貝合わせ is not a
    # chapter of anything, and filing it as one loses both the work and its author. Where the
    # categories and the thing disagree, the thing wins.
    split_anth = split_trial = 0
    for r in releases:
        parts = anth_parts(r.get("ep"))
        if not parts:
            continue
        author, title, is_trial = parts
        r["collection"] = r["work"]
        r["work"], r["author"], r["ep"] = title, author, title
        # One instalment, complete in itself. The container may run for years; this did not.
        r["type"], r["kind"] = "oneshot", "oneshot"
        r["kind_basis"] = "an instalment of a collection, complete in one part"
        if is_trial:
            # DEFINITIONS §6: a 試し読み is not web publication. The work is real and stays, with
            # its author; what changes is the claim about where it can be read. This is the same
            # web_status the platform-level trial rule sets, so the existing drop at the feed
            # boundary applies with nothing new to remember.
            r["web"] = "promotional-sample-only"
            r["type"] = "trial"
            r["kind_basis"] = "a preview instalment from a printed collection"
            split_trial += 1
        split_anth += 1
    for r in releases:
        if COLLECTION.search(r.get("work") or ""):
            r["in_collection"] = True
    print(f"anthology instalments split into their own author and title : {split_anth} "
          f"({split_trial} of them previews, kept as print candidates rather than web releases)")

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
        # Which of this source's dates are it importing a back catalogue rather than publishing.
        # Computed per file because the signature is a property of the source: 一迅プラス put 1972
        # chapters across 152 series on 2025-08-08, and ゆるゆり began in 2008.
        _stamped = importdates.stamps(_d.get("works") or [])
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
            # A promotional read-through is not a serialisation. ダ・ヴィンチニュース numbers the
            # instalments 第1回, 第2回 and one of ours says 全4回連載でお届けします outright: it is a
            # 試し読み of a finished tankobon. Counted as chapters it gave 三角形の壊し方 eleven
            # instalments and a run of dates that decided its state.
            #
            # Skipped whole rather than kept dateless, because taking the link and dropping the
            # dates would still list the shop as somewhere the work is published, which is the
            # claim being retracted. Every work reached this way has a real home elsewhere; the
            # last one without a home in our data, 百合にはさまる男は死ねばいい!?, is anchored to
            # comicブースト now. コミックノヴァ is NOT this kind of site and is not listed: it is a
            # publisher's own weekly serialisation that withdraws its older chapters.
            if any(h in (w.get("url") or "") for h in PROMO_HOSTS):
                continue
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
                "partial": True, "oneshot_src": False, "completed_src": None,
                "running_src": None, "_srcs": set(),
            })
            bucket["_srcs"].add(_d.get("platform") or _d.get("source") or "")
            bucket["oneshot_src"] = bucket["oneshot_src"] or oneshot_src
            # The platform's own statement that the serialisation is over, where it makes one.
            # カドコミ's serializationStatus takes three values across the works we hold — unknown
            # 217, ongoing 92, finished 91 — so `finished` is a real assertion and not a default.
            # カドコミ answers in English and comici in Japanese, in a field of the same name.
            # comici has no value meaning "we do not know": a page carrying the field has answered,
            # which is why 連載中 is worth recording as well and not only its opposite.
            platform_status = str(w.get("status") or "")
            if platform_status.lower() == "finished" or platform_status == "完結":
                bucket["completed_src"] = "the platform marks the serialisation finished"
            elif platform_status == "読み切り":
                bucket["oneshot_src"] = True
            elif platform_status in ("ongoing", "連載中"):
                bucket["running_src"] = "the platform marks the serialisation as running"
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
                    _au, _ti, _trial = _am
                    if _trial:
                        # A preview is not something a reader can read here, so it does not become
                        # a row in the works tab. The work is real and belongs to the printed
                        # collection; the collection is what the volumes tab carries. Skipping it
                        # here is the same judgement the feed makes, made in the second place that
                        # reads this function, which is why the function returns the fact rather
                        # than each caller re-deriving it from the title.
                        continue
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
                # A skipped slot is not an instalment. Diverted rather than dropped: the date is
                # evidence about the schedule and REQUIREMENTS keeps what it observed. Counting
                # these gave 19 works an inflated `chapters`, and would let a notice become
                # `latest`, which it had done for 清田さんは汚されたい!?.
                if is_skipped_slot(c.get("title")):
                    bucket.setdefault("skipped", []).append(
                        {"title": c.get("title"), "date": str(c.get("updated") or "")[:10]})
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
                # A date only counts as an import where EVERY source giving it says so. One source
                # importing a chapter another source watched appear does not unmake the observation.
                if (w.get("work_title"), str(c.get("updated") or "")[:10]) not in _stamped:
                    slot["date_observed"] = True

    # Collapse each bucket's merged chapters into the row the interface reads.
    for row in series.values():
        chs = sorted(row.pop("chapters").values(), key=lambda c: str(c.get("updated") or ""))
        row["chapters_list"] = chs
        row["chapters"] = len(chs)
        dated = [c for c in chs if c.get("updated")]
        row["dated"] = len(dated)
        # THE HEADLINE DATES COME FROM CHAPTERS SOMEBODY WATCHED APPEAR. A platform importing its
        # back catalogue stamps every chapter with the day it imported, and that date is real and
        # is kept (§4); it is simply not a publication date, and 34 works were reading `active` or
        # `slow` on one. Where a whole run is stamped there is nothing better in this row, so the
        # stamp still shows and the row says so, and the merge across platforms prefers a source
        # that watched something happen.
        observed = [c for c in dated if c.get("date_observed")]
        face = observed or dated
        row["dates_imported"] = bool(dated) and not observed
        row["first"] = str(face[0]["updated"])[:10] if face else None
        row["latest"] = str(face[-1]["updated"])[:10] if face else None
        row["latest_ep"] = (face[-1].get("title") or "").strip() if face else ""
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
        # ENDED, on the platform's own words rather than on silence.
        #
        # Two firm signals, and only these two. A chapter titled 最終話 is the publisher saying so in
        # the one place they always say it; カドコミ also carries an explicit status field.
        # 会長！今日はサボりましょう！ has a 最終話 dated 2025-01-30 and we filed it `dormant` — which
        # reads as an abandoned series rather than a finished one.
        #
        # What is NOT evidence: silence, a stale 次回更新予定日：未定, or an absent update. カドコミ
        # leaves that work's serializationStatus at "ongoing" to this day, and the 最終話 itself is
        # isActive: false — withdrawn along with most of the run, so a reader cannot see the ending
        # on the page at all. The line between "ended" and "hiatus that may never resume" is real
        # and this does not try to guess it: without one of the two signals a quiet work stays
        # `dormant`, which describes the observation instead of inferring an intention.
        # Matched on the folded form, because a title may spell its numbers full-width, and
        # quoted from the raw one where that also matches, so the basis says what the page says
        # rather than what NFKC made of it: ＜完＞ folds to <完> and the publisher wrote neither.
        _ep_raw = row.get("latest_ep") or ""
        # A capture the platform itself says is short cannot claim to be the series. Marked partial
        # so the count reads as ours rather than as the work's, and where we are not holding the
        # platform's newest chapter the silence is ours too, so no state is inferred from it.
        _sl = stated_len.get(norm_work(row.get("work") or ""))
        _short = bool(_sl and _sl["n"] > (row.get("chapters") or 0))
        if _short:
            row["partial"] = True
            row["chapters_stated"] = _sl["n"]
            _at_end = _sl.get("holds_last")
            if _at_end is None and _sl.get("last_episode_url"):
                _at_end = (row.get("url") or "").rstrip("/") == _sl["last_episode_url"]
            row["_capture_behind"] = not _at_end
        _fm = FINAL_RE.search(unicodedata.normalize("NFKC", _ep_raw)) if _ep_raw else None
        _fm_shown = (FINAL_RE.search(_ep_raw) or _fm) if _fm else None
        _final = bool(_fm)
        _completed = row.pop("completed_src", None)
        _running = row.get("running_src")
        if row.pop("_capture_behind", False) and not (_final or _completed):
            # The platform lists chapters past the newest we hold, so our newest is not the
            # series' newest and its age measures our capture rather than the work.
            row["state"] = "unknown"
            row["state_basis"] = (
                f"{_sl['n']} chapters are listed on the platform and we hold {row['chapters']}, "
                f"none of them the newest, so nothing here says when this last updated")
        elif not row["latest"]:
            row["state"] = "unknown"
        elif row["oneshot"]:
            row["state"] = "oneshot"
        elif _final or _completed:
            row["state"] = "completed"
            # Quoting what was actually found. The pattern accepts 最終話 and a bracketed 完
            # alike, and a basis naming the wrong one is a citation to something the page does
            # not say.
            row["completed_basis"] = (f"the newest chapter is titled {_fm_shown.group(0)}"
                                      if _final
                                      else _completed)
        else:
            # Skipped slots bear on this twice over, and in opposite directions.
            #
            # As LIVENESS: publishing hiatus art on schedule is more than silence tells you, so the
            # age runs from the most recent event of either kind. A monthly series that skipped
            # last month is not drifting toward dormant.
            #
            # As HIATUS: one skip is a skipped period rather than a suspended series. For a monthly title
            # it is routine. It takes a RUN of them with no chapter in between before the series
            # itself is fairly called paused, and even then only while the newest is fresh
            # (HIATUS_FRESH_DAYS); an old notice has stopped describing the present.
            _sk = sorted((x["date"] for x in (row.get("skipped") or []) if x.get("date")))
            _after = [d for d in _sk if d > row["latest"]]
            _newest = max([row["latest"]] + _after)
            age = (_today - datetime.date.fromisoformat(_newest)).days
            row["age_days"] = age
            if len(_after) >= 2 and age <= HIATUS_FRESH_DAYS:
                row["state"] = "hiatus"
                row["state_basis"] = (f"{len(_after)} consecutive skipped slots since the last "
                                      f"chapter, newest {_after[-1]}")
            else:
                row["state"] = "active" if age <= 45 else ("slow" if age <= 365 else "dormant")
                # SILENCE IS NOT A BASIS ON ITS OWN, and until now dormant carried none at all:
                # 150 works asserted it with nothing behind them. Saying what it rests on makes the
                # weakness visible instead of leaving it implied.
                row["state_basis"] = (
                    f"no chapter for {age} days, and nothing states it has ended")
                # A PLATFORM SAYING IT IS RUNNING IS NOT SILENCE. It does not make a quiet work
                # active, because a serialisation can be open and on hiatus at once, and the
                # silence is still what we observed. What it does is say the silence is ours: the
                # publisher has not ended this, so the reader is owed the distinction between a
                # work nobody has closed and a work nobody has touched. カドコミ marks six of its
                # ten dormant works ongoing, and it is also what keeps an aggregator's 完結 tag
                # from closing a work the platform itself still calls running.
                if row.pop("running_src", None):
                    row["state_basis"] = (
                        f"no chapter for {age} days in what we hold, but the platform still marks "
                        f"the serialisation as running")
                # THE ANTENNA SAYS IT FINISHED. An aggregator's tag is a lead, so it does not carry
                # a live series on its own; joined to a year of silence it is better evidence than
                # the silence alone, which is all `dormant` ever had.
                # PERSUASIVE UNLESS SOMETHING CONTRADICTS IT, which is the project owner's
                # reading and a better test than the age of the silence. A tag was first honoured
                # only past a year, which threw away exactly the cases it fits best: a series is
                # tagged 完結 when it ends, so the tag is freshest while the last chapter is still
                # recent. Sixteen works read `slow` for that reason alone, and three read `active`
                # on a final chapter or an incidental one.
                #
                # What would contradict it is a chapter published AFTER we saw the tag. Across all
                # 90 tagged works there is not one, so nothing in our own data argues against any
                # of them. Where there is one, the tag is stale and the work speaks for itself.
                _rev = reviewed.get(norm_work(row.get("work") or ""))
                if _rev and _rev.get("verdict") == "completed":
                    row["state"] = "completed"
                    row["completed_basis"] = (
                        f"{_rev['basis']} ({_rev.get('source') or _rev.get('source_kind')}"
                        + (f", {_rev['source_url']}" if _rev.get("source_url") else "") + ")")
                    if _rev.get("ended_on"):
                        row["ended_on"] = str(_rev["ended_on"])
                    continue
                if _rev and _rev.get("verdict") == "continuing":
                    # Looking showed the opposite. Kept, so the next pass does not pay to find it
                    # again, and so the state says a person checked rather than that nobody had.
                    row["state_basis"] = f"reviewed and found still running: {_rev['basis']}"
                    continue
                _shop = shop_completed.get(norm_work(row.get("work") or ""))
                if _shop:
                    row["state"] = "completed"
                    row["completed_basis"] = (
                        f"BOOK☆WALKER lists this series as 完結 ({_shop.get('url')})")
                    continue
                _seen = completion_claims.get(norm_work(row.get("work") or ""))
                if _seen and row["latest"] <= str(_seen)[:10]:
                    row["state"] = "completed"
                    row["completed_basis"] = (
                        f"the comparator lists this work as 完結, seen {_seen}, and no chapter has "
                        f"appeared since; the newest we hold is {row['latest']}")
                elif _seen:
                    row["state_basis"] = (
                        f"the comparator listed this work as 完結 on {_seen}, and a chapter has "
                        f"appeared since, on {row['latest']}, so the tag is not acted on")
            if _after:
                row["skipped_since_chapter"] = len(_after)
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
        # A row whose every date is an import stamp cannot speak for the work's state, so it loses
        # to any row that can, however many chapters it holds. 一迅プラス holds all 77 chapters of
        # ナメられたくないナメカワさん at 2025-08-08 and コミックDAYS watched the run end in 2022.
        rows.sort(key=lambda r: (not r.get("dates_imported"), r["chapters"], r["latest"] or ""),
                  reverse=True)
        # The sources that hold an observed date, where any does. This is what stops a known
        # import stamp being published as the work's latest when another source knows better.
        # Where every source is an import stamp we do not know when this work last updated, and
        # taking the newest stamp is the worst of the answers available: 2DK、Gペン、目覚まし時計。
        # read `dormant` off コミックDAYS's 105 chapters while displaying 一迅プラス's 2026-06-05,
        # so the headline date contradicted the state beside it. Falling back to the row that
        # decided the state keeps the two saying the same thing.
        _dr = [r for r in rows if not r.get("dates_imported")] or rows[:1]
        best = rows[0]
        # THE STATE HAS TO DESCRIBE THE WORK, NOT ONE PLATFORM'S COPY OF IT. `best` is a single
        # row and the headline date is merged across every row, so a work still updating on one
        # platform read `dormant` off another that was behind: きみが死ぬまで恋をしたい shipped
        # dormant beside a chapter three weeks old, and nine more shipped `slow` beside chapters a
        # week old. Only the age-based states are recomputed. `completed`, `oneshot` and anything a
        # reviewer decided rest on evidence rather than on arithmetic, and are left alone.
        _merged_latest = max((r["latest"] for r in _dr if r["latest"]), default=None)
        _state, _state_basis = best["state"], best.get("state_basis")
        # EVERY DATE THIS WORK HAS IS A STAMP. Not a work that went quiet: a work whose whole run
        # arrived on the day a platform imported it, so its dates say when we were told about it
        # and nothing about when it published. あなたの夜が明けたら is a 作品集 posted in one day and
        # read "no chapter for 550 days", which is the same sentence a stalled serialisation gets.
        # `completed` and `oneshot` are untouched, because they rest on evidence rather than on
        # arithmetic over these dates.
        if (_state in ("active", "slow", "dormant")
                and all(r.get("dates_imported") for r in rows)):
            _state = "unknown"
            _state_basis = ("every chapter we hold arrived on the day a platform imported the "
                            "series, so nothing here says when it last published")
        if _state in ("active", "slow", "dormant") and _merged_latest:
            _age = (datetime.date.today()
                    - datetime.date.fromisoformat(_merged_latest)).days
            _recomputed = "active" if _age <= 45 else ("slow" if _age <= 365 else "dormant")
            if _recomputed != _state:
                _state = _recomputed
                _state_basis = (f"no chapter for {_age} days on any platform we watch; the newest "
                                f"we hold is {_merged_latest}")
        works_out.append({
            "work": best["work"],
            "author": next((r["author"] for r in rows if r["author"]), ""),
            # The BEST-KNOWN length, not a sum: every source is describing the same story, and
            # adding them would report 135 chapters for a 121-chapter work.
            "chapters": best["chapters"],
            # What the platform says the series is long, where we hold less. Published so the
            # count can read as "what we have" rather than as the length of the work.
            **({"chapters_stated": best["chapters_stated"]}
               if best.get("chapters_stated") else {}),
            "partial": all(r["partial"] for r in rows),
            "latest": max((r["latest"] for r in _dr if r["latest"]), default=None),
            "latest_ep": best["latest_ep"],
            "first": min((r["first"] for r in _dr if r["first"]), default=None),
            "state": _state, "oneshot": best["oneshot"],
            # Why we say it ended, carried up with the state. A state without its basis is the
            # thing this project keeps having to unpick.
            # THE BASIS HAS TO DESCRIBE THE STATE BEING PUBLISHED. `state` comes from `best`, and
            # these took the first basis any row carried, so a work could publish one platform's
            # state beside another platform's reason for it. はなにあらし read `active` with its
            # last chapter a month old, above a line saying no chapter had appeared for 2946 days:
            # サンデーうぇぶり has 169 chapters ending last month, pixivコミック has 3 ending in
            # 2018, and the row took the state from one and the sentence from the other.
            "completed_basis": _basis_of(best, rows, "completed_basis"),
            # Same reasoning for a paused series: the state travels with what it rests on, and
            # the skipped slots themselves are kept as dated evidence rather than summarised away.
            # A recomputed state brings its own reason. Taking the row's would publish one
            # platform's explanation for a state that platform did not decide.
            "state_basis": (_state_basis if _state != best["state"]
                            else _basis_of(best, rows, "state_basis")),
            "skipped": sorted(
                {(x.get("date"), x.get("title")) for r in rows for x in (r.get("skipped") or [])},
                reverse=True),
            "collection": best.get("collection"),
            "url": best["url"],
            "free": best["free"], "free_timed": best["free_timed"], "priced": best["priced"],
            "sources": [{"platform": r["platform"], "url": r["url"], "chapters": r["chapters"],
                         "free": r["free"], "free_timed": r["free_timed"], "priced": r["priced"],
                         "latest": r["latest"], "partial": r["partial"], "format": r["format"]}
                        for r in rows],
            # WHAT THE PLATFORM SAYS, kept apart from what we work out. The coming-soon view
            # predicts from each series' own past interval, which is an inference and is labelled
            # one. A platform that prints 次回無料更新は8/21 has announced a date, and an
            # announcement and an average are not the same kind of thing.
            # A CADENCE IS PROJECTED FROM THE LAST CHAPTER, so it is only as good as that date.
            # 頂のリヴィーツァ carries 毎週木曜 and a newest chapter from August 2024, and the
            # arithmetic dutifully produced 2024-08-22 and called it overdue, which is true and
            # useless. Where we have just said we cannot date the work, or where every date it has
            # is a platform's import stamp, projecting from it contradicts what we said. The
            # platform's own announced date is untouched: that is a statement, not arithmetic.
            "stated_next": _with_cadence_date(
                next((dict(_ss, platform=r["platform"])
                      for r in rows
                      for _ss in [_stated_for(best["work"], r["platform"])] if _ss), None),
                # From the date we publish as the work's latest, not from the newest any row
                # holds: ハロー、メランコリック! ended in 2021 and projected from a 2025 import
                # stamp, so it announced a Saturday four years after its last chapter.
                #
                # And only where the work might still be running. A cadence is a statement about a
                # live serialisation, and a work silent for 1727 days is not one, whatever the
                # platform's page still says.
                _merged_latest
                if _state in ("active", "slow") else None),
        })
    # The works list is assembled from the source records rather than from the feed, so filtering
    # releases does not reach it. Both paths need the register, which is why dropping it in one
    # place looked like it had worked and had not.
    _wh = withheld_works()
    if _wh:
        _out = [r for r in works_out if norm_work(r.get("work")) in _wh]
        works_out = [r for r in works_out if norm_work(r.get("work")) not in _wh]
        if _out:
            print(f"withheld from works : {len(_out)} work(s) held back pending review: "
                  + ", ".join(r["work"][:20] for r in _out))

    # A shop listing is not a web work. Held out of the web list rather than deleted: the row is
    # still the truth about what カドコミ sells, and status.html counts what was set aside so the
    # number cannot quietly become a way of losing things.
    _aside = set_aside(works_out)
    catalogue_rows = [dict(r, set_aside=_aside[r["work"]]) for r in works_out
                      if r.get("work") in _aside]
    works_out = [r for r in works_out if r.get("work") not in _aside]
    if catalogue_rows:
        import collections as _c
        for _why, _n in _c.Counter(r["set_aside"] for r in catalogue_rows).most_common():
            print(f"set aside           : {_n} work(s), {_why}")

    series_rows = sorted(works_out,
                         key=lambda r: (r["latest"] or "", r["chapters"]), reverse=True)
    # AUTOPILOT. Before attaching anything, give every work and author the pipeline currently knows
    # about a reading if it does not have one. This is what makes a title that appears overnight
    # render in English by morning with nobody touching it — the alternative is a store that only
    # grows when someone remembers to run a pass, which is not a database that can be left running.
    #
    # Offline, idempotent, and additive only: a name with a reading from a real source is never
    # overwritten by a guess. If SudachiPy is not installed it does nothing and the interface falls
    # back to Japanese (§6), which is a documented state rather than a failure.
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters" / "names"))
        import pass4_analyser as _p4
        _p4.fill_missing({r["work"] for r in series_rows}, "titles")
        _p4.fill_missing({(r.get("author") or "").strip()
                          for r in series_rows if r.get("author")}, "authors")
        # Chapter names and credit lines — 202 of the former against 6 titles, so this is most of
        # what stays Japanese on an English page.
        # Titles as phrases too, so one whose only Japanese is punctuation (IDOL×IDOL STORY！) is
        # covered; the title store keys on readings and skips those entirely.
        _p4.fill_chapters({x for r in releases + series_rows
                           for x in (r.get("ep"), r.get("latest_ep"), r.get("collection"),
                                     (r.get("author") or "").strip(),
                                     r.get("work")) if x})
    except Exception as e:                      # never let a naming helper break the build
        print(f"names           : automatic reading pass skipped ({e})")

    # Attach English names and readings. Keyed on the exact Japanese string the store was built
    # from, so a work or author with no entry simply gets nothing and renders in Japanese (§6).
    _auth_names, _title_names = load_names()

    # PUNCTUATION-TOLERANT LOOKUP. The store is keyed on the exact Japanese string, and the same
    # work reaches us with both （私に） and (私に) depending on the platform — full-width and
    # half-width brackets are different characters, so one variant matched and the other silently
    # got nothing. NFKC folds the two together without touching the words, so a lookup miss falls
    # back to the folded key rather than giving up.
    def _fold(t):
        return unicodedata.normalize("NFKC", t or "").replace(" ", "")

    # A withheld work's TITLE must not ship either. names.json is keyed by folded title and is
    # published, so leaving it here would put the work's name and English rendering on the public
    # site with only its rows removed. Third path, and the reason each output was checked rather
    # than the first one being taken as proof.
    _wh_names = withheld_works()
    _title_names = {k: v for k, v in _title_names.items() if norm_work(k) not in _wh_names}
    _title_folded, _fold_lost = fold_map(_title_names, _fold)
    _auth_folded, _a_lost = fold_map(_auth_names, _fold)
    # Named for what they are rather than reusing a short loop name: `_dropped` is already bound
    # two thousand lines away in this function, and the shadowing budget counts that.
    for _folded_key, _folded_dups in _fold_lost + _a_lost:
        print(f"  note: {_folded_key} has {_folded_dups + 1} records that fold together; "
              f"kept the fullest")

    _named_w = _named_a = 0
    for r in series_rows + releases:
        # AN EXACT MATCH IS NOT AUTOMATICALLY THE BETTER ONE. The same work reaches us spelled
        # 勝たん！～ and 勝たん!～, and the store holds a record for each: the curated one carries
        # the translation, the other only an automatic reading. Taking the exact hit first meant
        # whichever spelling the interface happened to display decided whether the work had an
        # English name at all. Both candidates are considered and the fuller wins, which is the
        # same rule fold_map already applies to records that fold together.
        _cands = [x for x in (_title_names.get(r.get("work")),
                              _title_folded.get(_fold(r.get("work")))) if x]
        t = max(_cands, key=_fullness) if _cands else None
        if t:
            r["work_en"] = t
            _named_w += 1
        _a_raw = (r.get("author") or "").strip()
        a = _auth_names.get(_a_raw) or _auth_folded.get(_fold(_a_raw))
        if a:
            r["author_en"] = a
            _named_a += 1
    print(f"names attached  : {_named_w} rows with a title rendering, {_named_a} with an author "
          f"rendering (store: {len(_title_names)} titles, {len(_auth_names)} authors)")

    # NAMES SHIP SEPARATELY TOO, keyed by the folded string, because an ARCHIVED MONTH IS NEVER
    # REWRITTEN. That rule exists to stop a published date being revised (§5) and it was silently
    # freezing everything else with it: 2026-07 was written before any of this existed, so every
    # row in it showed Japanese only and always would have. Dates are the thing that must not
    # change; a romanisation improving is the system working.
    #
    # So the archive keeps its rows exactly as published and the interface joins the current names
    # onto them at render time. One file, loaded once, covering every month.
    (out / "feed" / "names.json").write_text(json.dumps(
        {"generated": str(_today),
         "note": "English renderings and readings, keyed by NFKC-folded title/author. Joined onto "
                 "feed rows at render time so archived months — which are never rewritten — still "
                 "show current names.",
         "titles": _title_folded, "authors": _auth_folded,
         # Chapter names, collections and credit lines, keyed folded like the rest.
         # phrases carries collection and chapter names, and a withheld work's title lands here
         # too when it names a collection. Filtered on the same register.
         # phrases carries collection and chapter names, and a withheld work's title lands here
         # too when it names a collection. Same register, or the title ships anyway.
         "phrases": {_fold(k): v for k, v in (
             (yaml.safe_load(pathlib.Path("data/names/phrases.yaml").read_text()) or {}
              ).get("names", {}) if pathlib.Path("data/names/phrases.yaml").exists() else {}
         ).items() if norm_work(k) not in _wh_names}},
        ensure_ascii=False, indent=1, default=jsonable))

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

    write_feed_split(out, releases, _today, platforms, plat_meta, lapsed,
                     contradicted_works, print_candidates, web_works, samples, regenerate=set(ARGS.regenerate_archive))

    cl = write_run_record(out, _today, releases, platforms, works, series_rows,
                          claim_trace, dropped_dupes, thin_dropped, resolver_dropped,
                          filled_author, filled_access, samples, catalogue_rows)

    print(f"syndicated      : {sum(1 for r in releases if r.get('syndicated'))}")
    print(f"provenance      : {dict(Counter(r.get('provenance') for r in releases))}")
    print(f"update kind     : {dict(Counter(r.get('kind') for r in releases))}")
    print(f"free view       : {sum(1 for r in releases if r.get('free'))} of {len(releases)}")
    print(f"samples dropped : {len(samples)} (promotional 試し読み — kept as print candidates)")
    print(f"identification  : {dict(Counter(r.get('ident') for r in releases))}")
    am = Counter(m for r in releases for m in (r.get("access_modes") or []))
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

    # THE SHOW MUST GO ON. Runtime mode counts violations and reports them; it never aborts. Each
    # invariant names the fallback the build has already applied, so what is published is degraded
    # rather than broken, and the count is the tripwire. The same checks BLOCK at check-in, where
    # someone is present to fix them — see docs/STANDING-INSTRUCTIONS.md §7.
    try:
        import subprocess as _sp
        sys.stdout.flush()          # the child writes straight to the fd; without this its output
                                    # lands ahead of the build's own buffered lines and reads as
                                    # though the checks ran before the thing they check.
        _sp.run([sys.executable, str(pathlib.Path(__file__).parent / "check.py"), "--runtime"],
                timeout=180)
    except Exception as _e:
        print(f"checks          : could not run ({_e})")


if __name__ == "__main__":
    main()
