#!/usr/bin/env python3
"""Merge source layers, validate, and compile the published dataset.

Source records (data/source/<source>/) are stored as fetched and never edited. Curation lives in
data/overlay/ and always wins. This step merges them by source priority, enforces the validation
rules in REQUIREMENTS §6, and writes data/build/.

Fails closed: any validation error aborts the build without writing.

Usage:  build.py [--out data/build]
"""
import argparse, datetime, glob, json, pathlib, re, statistics, sys, unicodedata
import urllib.parse as urlparse
from collections import Counter, defaultdict

sys.path.insert(0, "adapters")
from crossplatform import carriage, episode_key, merge_releases  # noqa: E402

import yaml
# Imported for its effect and not for a name: it points yaml.safe_load at libyaml, once, for every
# read below and for every read any adapter this file imports will do. Without it this build spends
# about 40 seconds per pass over data/ in the pure-Python parser. Do not "tidy" the unused import
# away; adapters/yamlfast.py says what it does and what was proved before it was turned on.
import yamlfast  # noqa: F401,E402
from facts import romanisation as _romanisation  # noqa: E402
from facts import credit as _credit_fact  # noqa: E402
from facts import reading as _reading  # noqa: E402
from facts import division as _division  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
import checkstate  # noqa: E402
from facts import identity  # noqa: E402
from facts import dating as _dating  # noqa: E402
import importdates  # noqa: E402
import isbndate  # noqa: E402
from names import credits as _credits  # noqa: E402
from names import gloss as _gloss  # noqa: E402
from names import key as _namekey  # noqa: E402
from names import openbd_reading  # noqa: E402
import bylines as _bylines  # noqa: E402
from classify import credence  # noqa: E402
from recon import bookwalker_volumes  # noqa: E402
import delivery  # noqa: E402
from facts import script as _script                                     # noqa: E402

# REQUIREMENTS §1. A field whose provenance is not here fails the build.
# Tier A/B attesting sources only. Discovery-only sources (Tier C/D) never appear here — they feed
# data/queue/, which is deliberately outside the source tree so nothing can promote a candidate
# into a record by accident.
ALLOWED_SOURCES = {"madb", "openbd", "ndl", "openbd-jpro", "publisher", "ichijinsha",
                   "gigaviewer", "kadokomi", "comicfuz", "webpages", "comparators", "nicovideo",
                   "pixivcomic", "reachable",
                   # A licensed retailer, admitted as a WORK source on 2026-08-06 by the project
                   # owner's decision. BOOK☆WALKER states no ISBN, so nothing in Tier A or B can be
                   # reached from its shelf and there is no catalogue record to promote instead:
                   # what the shop says is all there is. It carries no marketing_label (§4), it
                   # admits under §2's comparator branch, and every record names the shelf it came
                   # from. The trade is 2,093 works we would otherwise not hold against being wrong
                   # later about some of them.
                   "bookwalker",
                   # The national bibliography again, reached by title and a person's name rather
                   # than by an ISBN, because BOOK☆WALKER states none. A separate directory from
                   # `madb` and not a second kind of record inside it: what is stored is a date
                   # for a work another source already holds, and the join it rests on is written
                   # into the record. See adapters/madb/by_title.py for what had to agree.
                   "madb-title",
                   # Carries no records at all: one content-flag register, written by
                   # adapters/madb/by_platform_isbn.py when attaching a book run to a serialisation
                   # turns up an imprint DEFINITIONS §7 designates. It is not in `madb/` because
                   # `load_dir` reads every yaml there as a work record, and it is not in the
                   # platform's own directory because the imprint is the bibliography's statement
                   # rather than the platform's.
                   "editions"}

# Sources carrying work-level records that merge into a work. Others (release feeds) are
# platform-level and compile separately.
WORK_SOURCES = {"madb", "openbd", "ndl", "openbd-jpro", "publisher", "ichijinsha", "bookwalker",
                "madb-title"}

# REQUIREMENTS §2. Covers may only be referenced from a publisher-supplied reuse feed.
ALLOWED_COVER_HOSTS = {"cover.openbd.jp"}

# Field-level priority when sources disagree (REQUIREMENTS §1: A > B > C).
# A retailer sits below every catalogue and every publisher: it answers for its own stock and for
# nothing else, so anything else that speaks about a field wins.
PRIORITY = {"madb": 10, "ndl": 10, "openbd": 9, "publisher": 5, "ichijinsha": 5, "bookwalker": 2}


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
# A SEASONAL GREETING IS A CARD, NOT AN INSTALMENT. 作りたい女と食べたい女 posted 暑中見舞い2026
# and it counted as that work's newest chapter, so the page reported a greeting where a reader
# looked for the story. 見舞い and 年賀 are the greeting-card words themselves and carry no story
# sense; 夏 and 新年 are not here, because a chapter is legitimately titled for a season and the
# rule has to miss those. It appears once a year, which is why nothing caught it sooner.
NON_STORY_RE = re.compile(r"告知|お知らせ|カバー|PV|特報|予告|特典|コミックス第[0-9０-９]+巻|重版"
                          r"|暑中見舞|残暑見舞|寒中見舞|年賀")
# Extras and side stories count on the CHAPTER side: おまけ, 番外編 and 外伝 are content a reader
# follows the series for, unlike an announcement or a cover reveal. They are instalments of an
# existing work, so they are never a new series either.
EXTRA_RE = re.compile(r"おまけ|番外編|外伝|特別編|幕間")
# Several publishers say so in the title rather than anywhere structured: 【読切】吸血少女と…,
# 【コミックDAYS読み切り】私のヒーロー, 読み切り作品, and 魔法使いの作庭/よみきり which puts it in
# the WORK title. Confirmation establishes is_oneshot properly but only reaches works we discovered
# through editorial coverage; this catches the rest, which were arriving as 新話.
ONESHOT_RE = re.compile(r"読切|読み切り|よみきり")

# WHY A ROW IS CALLED A ONE-SHOT: the routes, strongest first, each with the sentence a reader is
# shown for it in both languages.
#
# WHY THE SENTENCE IS REQUIRED. A one-shot's length is published without a hedge, as "1 chapter",
# where a serialisation reads "at least 1 chapter", because the count is a floor for one and the
# whole work for the other. So the page is asserting that a story is complete, which is the claim
# that misleads if it is wrong, and until this table existed all 399 one-shot rows carried no basis
# at all. An inference has to be recorded AS an inference with its reasoning, and never written as
# though a source said it.
#
# `inferred` is the whole point of the ranking. The first five are a platform or a reviewer stating
# what the work is. The last three are us reading a shape, and each is defensible and none is a
# statement: a single instalment named after its work is how platforms name a 読切 and is also how
# a serialisation's first chapter can be named.
ONESHOT_WHY = {
    "review": (None, None, False),                        # the register supplies its own sentence
    "platform-status": ("{plat} states the serialisation status 読み切り",
                        "{plat}が連載状況を読み切りと表示している", False),
    "platform-confirmed": ("{plat} states that this work is a one-shot",
                           "{plat}自身がこの作品を読み切りとしている", False),
    "every-chapter-marked": ("every instalment here is marked 読切",
                             "掲載されている話すべてに読切の表示がある", False),
    "work-title-marked": ("{plat} writes 読切 into the work's own title",
                          "{plat}が作品名自体に読切と書いている", False),
    "collection-instalment": ("one story out of a collection, filed as the work it is",
                              "作品集の一編で、それ自体を作品として扱っている", False),
    "feed": ("the release this work published was typed a one-shot where it appeared",
             "公開時の話が読み切りとして扱われている", False),
    "self-named": ("the single instalment is named after the work, which is how a one-shot is "
                   "named and is our reading rather than a statement",
                   "唯一の話の題名が作品名と同じで、読み切りの付け方だが、我々の読みであって"
                   "表示ではない", True),
}
# A ROUTE THAT IS NOT HERE, AND WHY. A prize citation standing where a chapter name goes is already
# read as one instalment by `is_prize_entry`, in the feed, and every one of the 13 prize-shaped
# single-instalment rows in the corpus reaches a stronger route than a rule here could offer: five
# by the release the feed typed, seven by a platform stating 読み切り, one by its own name. A second
# rule for them would have changed nothing and reported clean forever (§4). What the series path
# genuinely lacked from that shape was the NUMBER: `stated_chapter_number` was reading 第28回 out of
# a contest citation and publishing it as a length.
# Strongest first. A row reached by two routes says the better one, so a work whose platform states
# 読み切り does not publish our guess about its title instead.
ONESHOT_RANK = {k: i for i, k in enumerate(ONESHOT_WHY)}


def oneshot_basis(why, plat=None):
    """(English, Japanese, inferred) for one route, or (None, None, False) where it says nothing."""
    en, ja, inferred = ONESHOT_WHY.get(why) or (None, None, False)
    fmt = lambda s: s.format(plat=plat or "the platform") if s else None   # noqa: E731
    return fmt(en), fmt(ja), inferred


def stronger(a, b):
    """Whichever of two route names ranks higher, ignoring an absent one."""
    if not a:
        return b
    if not b:
        return a
    return a if ONESHOT_RANK.get(a, 99) <= ONESHOT_RANK.get(b, 99) else b

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



def _interpunct_rulings(fields):
    """`{folded credit: 'one' | 'several'}` for every ・ the corpus can settle. `{}` on any failure.

    ONE PRODUCER, ASKED ONCE (§3). The naming pass and the credit division both need this answer,
    and computing it twice off two slightly different field sets is how the store and the page came
    to disagree about how many people `くろば・Ｕ` names in the first place.

    It prints what it could not settle, because a string waiting on a person is the thing somebody
    has to act on and a count alone would not say which one.
    """
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
        from facts import credit as _ip
        from names import inputs as _in
        whole = lambda f: [n for n, _r in _in.split_authors(f, interpunct=False)]   # noqa: E731
        rulings = _ip.load_rulings()
        got = _ip.settled(fields, whole, rulings)
        held = _ip.unruled(fields, whole, rulings)
        print(f"credits         : {len(got)} interpunct credit(s) settled from the corpus, "
              f"{len(held)} waiting on a person"
              + (": " + ", ".join(held) if held else ""))
        return got
    except Exception as _e:                                                     # noqa: BLE001
        print(f"credits         : no interpunct ruling ({_e})")
        return {}


def credit_parts(ja, store=None, ruled=None):
    """How one credit field divides, in the shape kari/app.js renders it from, or None.

    `{"p": [{"n": name, "r": role}, …], "etc": 1, "part": 1}`. `etc` says the field names some of
    its contributors and stops; `part` says this division does NOT account for everything the field
    says, which is the flag that stops the interface rebuilding a byline out of an incomplete
    answer.

    SHIPPED RATHER THAN DERIVED IN THE BROWSER, so the reader's romanisation style, name order and
    furigana all reach a credit line, and so that the division a page draws is the division the name
    store is keyed on. `adapters/names/creditline.py` holds the rule; this only calls it.

    EVERY FIELD AND NOT ONLY THE PHRASED ONES. This was keyed off `data/names/phrases.yaml`, so a
    credit field with no analyser phrase shipped no division at all and the interface fell back to
    dividing the string itself. 2,700 fields reach a reader and 236 of them were rendering in
    Japanese under an English heading for want of an answer this function already had.
    """
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
        from names import creditline
    except Exception:                                                       # noqa: BLE001
        return None
    parts, drop = creditline._divide(ja or "", store, ruled)
    if not parts:
        return None
    out = {"p": parts}
    if drop:
        # Literal substrings of the field that say the same thing twice: a reading printed beside
        # the name it reads. Taken off an English page, where kana beside a romanisation is a
        # second copy of a name in a script the page is not written in.
        out["drop"] = drop
    if creditline.coverage(ja or "", store, ruled):
        out["part"] = 1
    return out


def floor_reader():
    """A katakana reading for a Japanese string or for one character, or None.

    THE SAME TWO ANSWERS THE STORE IS FILLED FROM. `analyse_best` reads a string the analyser
    recognises and `per_char` reads a character alone, falling through to Unihan, so the floor and
    the readings in `data/names/` come from one place. A third opinion about how a character is
    read is what §3 says will disagree with the other two.

    MISSING SudachiPy IS NOT AN ERROR here any more than it is for the autopilot: the floor is
    empty, the count printed beside it says so, and `English mode has no Japanese` is what makes
    that visible rather than quiet.

    Cached, because a run appears in dozens of credit fields and the analyser is the slow half.
    """
    try:
        from sudachipy import Dictionary, SplitMode
    except ImportError:
        return lambda _s: None
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters" / "names"))
    import pass4_analyser as _p4
    tok = Dictionary().create()
    modes = [SplitMode.C, SplitMode.A]
    seen = {}

    def read(s):
        if s not in seen:
            seen[s] = (_p4.per_char(tok, modes, s) if len(s) == 1
                       else _p4.analyse_best(tok, s, modes)[0])
        return seen[s]

    return read


def credit_fields(idx, works, series_rows, releases, registry=None):
    """Every credit field a reader can meet, from the five collections that carry one.

    READ OFF THE BUILT COLLECTIONS AND NOT OFF A NAME FILE. The division has to answer for the
    string the INTERFACE looks up, which is `index[].c` on the catalogue tab, `works[].creator` on
    the 発売 tab and `author` on the other two. A set assembled from anywhere else answers for
    strings nobody renders and misses the ones somebody does.

    THE REGISTRY IS THE FIFTH, and it holds strings no feed row does. `iimAn&惟丞` and
    `水谷悠珠＆かえで透` were single credits before a splitter divided on the ampersand; the registry
    is append-only so both spellings stay, and a credit page heads with one and a homophone list
    links to it. Without a division those pages showed the joined spelling in Japanese.
    """
    seen = set()
    for rows, key in ((idx or [], "c"), (works or [], "creator"),
                      (series_rows or [], "author"), (releases or [], "author")):
        for r in rows:
            v = (r.get(key) or "").strip() if isinstance(r, dict) else ""
            if v:
                seen.add(v)
    for fact in ((registry or {}).get("credits") or {}).values():
        v = str((fact or {}).get("credit") or "").strip()
        if v:
            seen.add(v)
    return sorted(seen)


def _floored(text, floor):
    """`text` with every Japanese run replaced by the floor's spelling of it, or None.

    THE BUILD'S ONE ROMANISER, ASKED RATHER THAN COPIED. `adapters/names/romfloor.py` spells every
    Japanese run any surface can carry and `build` ships the answers, so the notation around a name
    is spelled here by looking the run up. A second speller in this function is the shape §3 counts
    seven shipped bugs from, and it would disagree with the map the browser reads.

    None WHERE A RUN IS NOT IN THE MAP, so a caller falls back rather than printing a hole. The
    styles are collapsed to the macron one for the reason `_recompose_credit` gives: a phrase is
    rendered once at build time and cannot follow the reader's choice.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
    from names import romfloor as _rf
    out, at = [], 0
    for m in _rf.JAPANESE_RUN.finditer(str(text or "")):
        got = (floor or {}).get(_rf.fold(m.group(0)))
        if not got:
            return None
        out.append(text[at:m.start()])
        out.append(got if isinstance(got, str) else got.get("macron"))
        at = m.end()
    out.append(text[at:])
    # THE FOLD THE RUNS ALREADY HAD, applied to what sits between them. `ＭＡＸ` is not a Japanese
    # run, so it went through raw and `まんがタイムきららＭＡＸ編集部` shipped as
    # `MangataimukiraraＭＡＸEditorial Department`, width intact and no space. The docstring above
    # claimed this function asked the one romaniser; it assembled a fourth pipeline and stopped one
    # step short of it.
    return _romanisation.normalise("".join(out))


def _person_shown(name, authors, floor, spell=False):
    """The English a credit line shows for one person, or None where nothing can spell them.

    THE SAME ANSWERS `kari/app.js` GIVES, asked in the same order, so that the phrase this file
    ships and the line the browser composes cannot disagree about a name (§3). `personShown` reads
    the store, then takes a name already in Latin as its own English form, then reaches the floor.
    Nothing here spells anything: the store holds the romanisations and `romfloor` holds the rest.

    A LATIN PEN NAME IS NOT A TRANSLITERATION OF ANYTHING (NAMES-PLAN §1), which is why the store
    is empty for `Magpie`, `IceFairy` and `sheepD` and always will be. NFKC and no more, which is
    the fold `plainLatin` applies for the same reason: `ＦＬＯＷＥＲＣＨＩＬＤ` is a cataloguer's
    typing of a name and not a different name.

    `spell` IS THE CALLER SAYING THIS RUN IS A PERSON, and without it only the store answers. The
    map these phrases live in holds chapter names and collection titles beside credit lines, the
    splitter finds a name-shaped run in plenty of them, and a floor that answers for anything would
    turn `のけもののまち` into `Nokemononomachi` and take the translation off `特別編4`. So the two
    later answers are offered only where the build has already divided the string as a credit
    field. Measured on the corpus this file was written against, letting them answer everywhere
    rewrote 1,573 titles and chapter names.

    None WHERE THE FLOOR HAS NO RUN EITHER, so a caller can decline rather than print a hole.
    """
    rec = authors.get(_namekey.fold(name)) or authors.get(name) or {}
    shown = ((rec.get("romaji") or {}).get("macron")) or rec.get("en")
    if shown or not spell:
        return shown or None
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
    from names import romfloor as _rf
    if not _rf.JAPANESE_RUN.search(name or ""):
        return unicodedata.normalize("NFKC", name)
    return _floored(name, floor)


def _credit_of_one(ja, detail, authors, floor, ruled, spell=False):
    """A field naming ONE person plus the job they did, with the job kept and the name current.

    WHAT THIS REPLACES, AND WHY THE THING IT REPLACES WAS WRONG IN A WAY NOTHING SAID. `[著]安田剛助`
    was left as the analyser wrote it, because `split_authors` peels the 著 off and a line rebuilt
    from its people alone would publish the name with the job gone. That protected the job and
    froze the name: a phrase is written once and never revisited, so the field still read
    `[ Cho ] Yasuda Takesuke` after openBD stated ヤスダ コウスケ, while the same man's name on its
    own read `Yasuda Kōsuke`. One person, two spellings, and a role bracket decided which. 207
    credit fields were in that state.

    NOTHING IS DROPPED. The person's own span is replaced by the store's rendering and the rest of
    the field keeps its place, spelled from the floor, so the 著 survives as `Cho`.

    THE ROLE IS ROMANISED AND NOT GLOSSED, and that is deliberate. kari/app.js holds `ROLE_EN` and
    `roleWord` is the one thing that turns 著 into `author`; a table of glosses here would be a
    second one, and `every credit role has an English gloss` asks the interface precisely so that
    there is only ever the one. Where the interface can draw this field it does, through
    `credit_parts`, and it says `author`. This is the string underneath that.

    THE DIVISION HAS TO ACCOUNT FOR THE WHOLE FIELD. `phrases.yaml` holds chapter names and
    collection titles as well as credits, and the splitter finds one name-shaped run in plenty of
    them: `100日後に咲く百合（MFC）` divides into one "name" and a bracket. `coverage` says what the
    division did not account for, and anything left is a string this has no business rewriting.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
    from names import creditline
    name, _reading, role = detail
    raw = str(ja or "").strip()
    # A FIELD THAT STATES NO JOB IS NOT A CREDIT WITH ITS ROLE TAKEN OFF. It is a title, a chapter
    # name or a name beside a note, and the leftover is not a bracket this may romanise away.
    if not role or creditline.coverage(raw, None, ruled):
        return None
    shown = _person_shown(name, authors, floor, spell)
    at = raw.find(name)
    if not shown or at < 0:
        return None
    head, tail = _floored(raw[:at], floor), _floored(raw[at + len(name):], floor)
    if head is None or tail is None:
        return None
    return (head + shown + tail).strip()


def _recompose_credit(ja, phrase, authors, ruled=None, floor=None, divided=False):
    """A credit line rendered from its people, or the phrase we already had.

    THE BAR WAS THE STORE AND IS NOW THE FLOOR, decided 2026-08-09. The line used to be rebuilt
    only where EVERY person in it had a rendering in the AUTHOR STORE, on the argument that half a
    line composed and half romanised whole reads as neither. That argument was about the fallback
    of the day, which was the analyser's one phrase for the whole string: two producers' spellings
    inside one line, and a reader unable to tell which half to trust.

    The floor is a different fallback. It renders each name in its own state, and `_person_shown`
    asks it in the same order `kari/app.js` asks it, so a composed line and a floored name are no
    longer two producers. What that leaves the rule protecting is a case that had stopped existing:
    of the 70 fields the budget counted, 60 were held back by somebody ALREADY IN LATIN. `Magpie`,
    `IceFairy`, `Kastel` and `sheepD` have no store record because a Latin pen name is not a
    transliteration of anything, so `it falls as those readings arrive` was false of them and no
    reading was ever going to arrive.

    AND THE READER HAD ALREADY LEFT. `creditFromParts` composes a multi-person line name by name
    and `personShown` cannot answer null in English, so of those same 70 fields the interface drew
    this phrase for four. The rule was defending a fallback nothing reaches, while the map went on
    shipping a spelling that disagreed with the page.

    So the bar is now that every person can be rendered SOMEHOW, and the phrase stands only where
    a name defeats the store, is not already Latin and holds a run the floor has never spelled.

    ONE PERSON IS A LINE OF ONE, and requiring two was the second producer §3 is about. The phrase
    map is written once per string by an analyser that divides by machine segmentation, so it holds
    `Ai Kawa Momoko` for あいかわももこ, `Ikedata Kashi` for いけだたかし and `Ara Fujipesu` for
    あらふじぺす, while the author store holds the same three people romanised from their readings.
    290 strings were answered twice, and the analyser's answer was the worse one every time it
    differed: it cuts where a tokeniser finds a word, and a pen name is not running text.

    The store wins because it is the thing corrections reach. A phrase is written once and never
    revisited, so a division sourced tomorrow would never have got into it.
    """
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
        from names.inputs import split_credits_detail
    except Exception:                                                       # noqa: BLE001
        return phrase
    # THE RULING ON A ・ TRAVELS WITH THE CALL. The splitter has taken a `ruled` map since the
    # interpunct work, and this caller was the one that never passed it, so a string the corpus had
    # settled as ONE person was still cut here: さりい・B came back as `Sarii, B` while the store
    # held `Sarii B`, and `a person is spelled one way` caught the pair. The splitter is one
    # producer only where every consumer asks it the same question.
    #
    # THE DETAIL AND NOT `split_authors`, because the role is what a line of one needs back.
    detail = split_credits_detail(ja or "", ruled=ruled)
    parts = [(n or "").strip() for n, _r, _role in detail]
    if not parts or not all(parts):
        return phrase
    # A ROLE IS PART OF WHAT THE LINE SAYS, and a line of one is the only place it survives. The
    # splitter peels `[著]` off before returning the name, so recomposing `[著]太陽まりい` from its
    # people would publish `Taiyō Marii` and drop the 著. `_credit_of_one` puts it back rather than
    # leaving the whole string as the analyser wrote it, which is what froze 207 spellings. A line
    # naming several people still loses its roles to the join, and that trade was made when this
    # was written.
    if len(parts) == 1 and parts[0] != (ja or "").strip():
        return _credit_of_one(ja, detail[0], authors, floor, ruled, divided) or phrase
    out = []
    for n in parts:
        # The ROMANISATION, not `en`. For a person `en` is written given-then-family, and the
        # interface shows a single author as the romanisation, family first: composing a line from
        # `en` put "Hitoma Iruma" beside "Kawakami Shion" in the same string. `_person_shown` reads
        # them in that order.
        #
        # Macron style, because a phrase is rendered once at build time and cannot follow the
        # reader's choice of macron, doubled or plain the way a single name does. That is a real
        # limitation of pre-rendering a line rather than its parts.
        shown = _person_shown(n, authors, floor, divided)
        if not shown:
            return phrase
        out.append(shown)
    return ", ".join(out)


VOLUME_NO = re.compile(r"^\s*(?:第\s*)?(?:v(?:ol)?(?:ume)?\s*\.?\s*)?(\d+)\s*(?:巻)?\s*$", re.I)


def volume_number(v):
    """The volume's number as a number, or None where it does not state one.

    MADB writes it a dozen ways: a bare `1`, `vol. 8`, `vol.2`, `volume 1`, `Volume1`, `volume.2`,
    `Vol. 1`, `v.1`, `第1巻`. 上 and 下 are not numbers, they are how a two-volume set is designated,
    and they answer None here.
    """
    m = VOLUME_NO.match(str(v.get("number") or ""))
    return int(m.group(1)) if m else None


def undated_publication(base):
    """`first_publication` for a work no source could date, from the record's own account of why.

    A WORK THAT EXISTS IS RECORDED WHETHER OR NOT WE CAN DATE IT (DEFINITIONS §6, amended
    2026-08-05). The scope test asks WHERE a work was first published and the date is not part of
    it, so refusing an undated work would be the database asserting that something it can see does
    not exist, on the strength of a field the source does not hold.

    AN UNDATED WORK STILL SAYS WHERE. This wrote `venue: None` on every one of them and so
    contradicted §6 in the branch whose comment cites it: WHERE is exactly what an undated work
    most needs to carry, and 1,209 records went out with it empty while every one of their source
    records stated a publisher.

    THE REASON IS THE SOURCE'S, NOT A PLACEHOLDER. `no-date-attested` was written over four
    different silences the capture had already told apart: an imprint that prints nothing, a
    chapter serial with no volumes at all, an imprint that dates its other books but not this one,
    and too little read to tell those apart. Each wants something different done about it and the
    flattened field asked for one thing. `no-date-attested` survives for the source that said
    nothing about why, which is the only case it was ever true of.

    The vocabulary and the sentence explaining each term are `recon/bookwalker_volumes`', because
    that is where a capture decides which silence a row is in. Nothing is restated here.

    THE DELIVERY DATE IS TAKEN WHERE NO PAPER RECORD IS REACHABLE, ruled by the project owner on
    2026-08-08 and recorded in DEFINITIONS §6 and docs/GAPS.md. `delivery.promote` decides, so the
    refusal that protects a printing lives in one place: where the shop states a print date the
    delivery date is refused, and this branch is only ever reached by a work no source could date at
    all. The date names the delivery and `date_event` says so, because `date` alone cannot tell a
    reader which event was dated.

    A ROW DATED THIS WAY IS FLAGGED, since this is the weakest date the database carries.
    `date_followup` is how these are found again, and `delivery.FOLLOWUP_NOTE` says why the count is
    not a queue length.
    """
    basis = base.get("date_basis") or "no-date-attested"
    undated = {
        "venue": base.get("venue") or base.get("publisher") or None,
        "date": None,
        "country": base.get("first_publication_country") or "JP",
        "date_basis": basis,
        # ASKED OF THE VOCABULARY, not of whichever capture happens to hold it. This named
        # `bookwalker_volumes` for both, which meant a reader of this line had to know that one
        # capture module carried the terms for a field three of them write to, and that the same
        # module holds the fallback sentence. `facts/dating` owns the space now.
        "venue_type": _dating.venue_type(basis),
        "note": _dating.note(basis),
    }
    items = (base.get("volumes") or []) + (base.get("chapters") or [])
    date, refused = delivery.promote(items)
    if not date:
        # A refusal here would mean a printed volume reached a branch for works with no date, so it
        # is recorded on the row instead of being dropped. Nothing has produced one yet.
        if refused:
            undated["date_refused"] = refused
        return undated
    followup = delivery.followup(
        base.get("edition_statement"),
        self_published=delivery.self_published(base.get("creator"), base.get("publisher"),
                                              base.get("imprint")))
    return {
        **undated,
        "date": date,
        "date_source": base.get("source") or None,
        "date_basis": delivery.BASIS,
        "date_event": delivery.EVENT,
        "date_followup": followup,
        # THE SILENCE THAT WAS THERE BEFORE THE DATE. `no-print-edition` and its siblings say why
        # the shop states no printing, and that reasoning is the ground for accepting a delivery
        # date at all, so it travels with the row instead of being overwritten by it.
        "date_silence": basis,
        "note": delivery.BASIS_NOTE[delivery.BASIS] + " " + delivery.FOLLOWUP_NOTE[followup],
    }


def readable_now(chapter, today=None):
    """Whether this chapter can be opened at no cost TODAY.

    A chapter that names the day it becomes free is not free before that day, whatever mode the
    capture filed it under. 一迅プラス prints 作品チケット対象です on every page of a series it runs
    tickets on, so the ticket probe answered yes for chapters that cost points; the adapter matches
    the per-chapter button now, and this is the backstop that reads what the row itself states.
    """
    when = str(chapter.get("free_from") or "")[:10]
    return not (when and when > (today or datetime.date.today().isoformat()))


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
# ASKED OF `facts/reading`, which owns which English name wins.
_EN_BASIS = _reading.en_ranks()

# And how much a claim about a READING is worth, same order, same reason. `analyser` and
# `back-converted` are a machine's answer and sit below every one that came from somewhere.
# `community-printed` is Wikidata, ruled noncanonical on 2026-08-09 and kept as a floor: an editor
# typed the kana, so it beats a machine reading the characters, and nobody answers for it, so it
# loses to a kana surface and to everything a source states. The owner's correction later that day
# left the rank alone, because this decides which of two records holds the better STRING and the
# corrected ruling is that a better string is exactly what Wikidata may give. Nothing measures a
# record's standing off this table.
# ASKED OF `facts/division`, which owns which reading wins. The reasoning that used to sit
# here is on the table, beside the bases it ranks.
_READING_BASIS = _division.ranks()


def _fullness(rec):
    """How much a name record actually says, for choosing between two that fold together.

    Field count alone was wrong the moment both records had an `en`. 見えてますよ！愛沢さん is
    held twice, and the copy carrying a curated translation lost to one carrying a community
    database's string, because the loser also happened to hold a reading, a ruby split and a set
    of furigana spans. Counting fields measured the wrong thing: what matters first is WHICH
    English name, and only then how much else is attached.

    AND THE SAME FAULT AGAIN ON THE READING, found by `a person is spelled one way`. 春結千晶 is
    held twice, once as itself and once with an ideographic space in it, and the spaced copy holds
    an analyser's `ハル ケツ 　 チアキ` while the plain one holds ハルユウチアキ off the shop that
    sells the artist's books. Neither has an `en`, so both scored zero twice over and the tie went
    to field count, which the analyser's copy wins by carrying the ruby, the spans and the two
    marks saying not to trust it. A reader was shown `Haru Ketsu Chiaki` with a [?] beside it while
    a researched reading of the same person sat in the file.

    So a reading a source states outranks a machine's, on the same order the name store ranks them
    by, and only then does field count decide.
    """
    if not isinstance(rec, dict):
        return (0, 0, 0, 0)
    has_en = 1 if rec.get("en") else 0
    rank = _EN_BASIS.get(rec.get("basis"), 0) if has_en else 0
    reading = _READING_BASIS.get(rec.get("reading_basis"), 0) if rec.get("reading") else 0
    rest = sum(1 for v in rec.values() if v not in (None, "", [], {}))
    return (has_en, rank, reading, rest)


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


# 第５０−２話 is chapter 50 part 2, written in fullwidth digits. NFKC folds the digits, and 第 is
# read in preference to the counter so a part number is not mistaken for the chapter number.
STATED_NUMBER = re.compile(r"第\s*(\d{1,4})")
COUNTER_NUMBER = re.compile(r"(\d{1,4})\s*(?:話|回|章|日目)")


def stated_chapter_number(ep):
    """The chapter number a work prints on its own newest instalment, or 0.

    A PRIZE CITATION IS NOT A CHAPTER NUMBER, and `is_prize_entry` is asked here for exactly the
    reason its own comment gives: the 28 in 【第28回角川漫画新人大賞】佳作 is the twenty-eighth
    CONTEST. The feed path has consulted that function since the day the citation shape was found,
    and this path did not, so one fact was read two ways (STANDING-INSTRUCTIONS §3) and the second
    reading reached a reader: 胡蝶の夢 published "28話" and ライオンと不時着(第17回NC佳作) "17話",
    both of them one-shots, both beside a 読切 badge saying so. Five rows, every one a work whose
    only instalment is its prize entry.
    """
    s = unicodedata.normalize("NFKC", str(ep or ""))
    if is_prize_entry(s):
        return 0
    m = STATED_NUMBER.search(s) or COUNTER_NUMBER.search(s)
    return int(m.group(1)) if m else 0


def one_row_per_work(idx, works):
    """Bibliographic rows collapsed so that one work is offered once, keeping every address.

    WHAT WAS WRONG. This list was one row per SOURCE RECORD, and the national bibliography holds
    several records for one book run: two spellings of an imprint split ゆるゆり and citrus in half,
    a run continued under a subtitle split 紅殻のパンドラ at volume 21, a shop's per-chapter edition
    sits beside the volumes, and one record carried the whole ISBD line as its name, so
    `School zone = スクールゾーン` stood next to `スクールゾーン`. 41 works were listed twice or
    three times, out of 2,558 rows.

    IDENTITY ALREADY ANSWERED THIS and nothing here asked it. `data/identity/works.yaml` joins
    records into works by anchor, the works tab has folded print records by it since the volumes
    tab was retired, and this list did not (STANDING-INSTRUCTIONS §3: one fact, two paths). So the
    registry is read here rather than a second grouping rule invented.

    NO ADDRESS IS LOST. `ids` carries every record the row stands for, because a collapse that kept
    one C-number would make the others unresolvable, and the published address is the `w`
    identifier, which resolves to all of them. The date is the earliest any record states.

    HOW LONG THE WORK IS, when two records both describe it. Not their sum: MADB holds ゆるゆり as
    21 volumes and as 11, overlapping, so adding them reports a work as twice its length, which is
    the fault `best_known_length` was written for. Not the larger either: スクールゾーン is volumes
    1 to 3 in one record and 4 and 5 in the other, so the larger is 3 and the run is 5, and
    紅殻のパンドラ continues from 21 into 22 to 25 under a subtitle. Both cases are answered by
    counting the DISTINCT volume numbers the records state, which is arithmetic on the numbering
    the publisher printed and owes nothing to either record's own count. Where a record numbers
    nothing there is no union to take, and the largest stated count is the floor.

    WHICH NAME THE ROW SHOWS. The first record by identifier, which is the same rule the works tab
    uses and prefers a C-number's bare title over a `madb-t-` record's ISBD line. That is why
    `School zone = スクールゾーン` disappears from the list without anything having to parse it.

    A ROW WITH NO IDENTITY STAYS ITS OWN. A record registered since the last identity run has no
    anchor here, and guessing which work it belongs to is exactly the merge this must not make.
    """
    reg = pathlib.Path("data/identity/works.yaml")
    if not reg.exists():
        return idx
    byanchor = identity.index((yaml.safe_load(reg.read_text()) or {}).get("works") or [])
    numbers = {w["work_id"]: [str(v.get("number") or "") for v in (w.get("volumes") or [])]
               for w in works if w.get("work_id")}
    out, at, held = [], {}, {}
    for row in idx:
        wid = byanchor.get(identity.print_anchor(row["id"]))
        if wid is None or wid not in at:
            row = dict(row, ids=[row["id"]])
            if wid is not None:
                at[wid] = row
                held[wid] = list(numbers.get(row["id"]) or [])
            out.append(row)
            continue
        kept = at[wid]
        kept["ids"].append(row["id"])
        held[wid] += list(numbers.get(row["id"]) or [])
        kept["n"] = max(kept.get("n") or 0, row.get("n") or 0)
        if row.get("d") and (not kept.get("d") or row["d"] < kept["d"]):
            kept["d"] = row["d"]
    for wid, row in at.items():
        # Every volume of every record has to state a number, or the union is counting a subset and
        # would report a work as SHORTER than one of its own records already says it is.
        vols = held.get(wid) or []
        if len(row["ids"]) > 1 and vols and all(vols):
            row["n"] = max(row["n"] or 0, len(set(vols)))
    return out


def demonstrable_length(rows, stated, latest_ep):
    """The most chapters we can show a work has, from every source that speaks to it.

    ONE NUMBER, ONE MEANING. The field used to hold the count of entries we hold, which is a fact
    about our coverage and not about the work, and it read as the work's length. It disagreed with
    the work's own numbering on 266 of the 386 rows where both could be seen, high on 239 and low
    on 27. Two different faults wore one number.

    The overshoot is fixed where the entries are counted, by collapsing an instalment split across
    parts. The undershoot cannot be: a platform showing twelve recent free chapters of a
    fifty-seven chapter serialisation is not hiding the rest from us, it simply does not publish
    them, and no arithmetic invents them.

    So the answer is the largest number any source demonstrates: what we hold, what the platform
    says it is long, and the number the work prints on its own newest chapter. Each is a floor and
    the truth is at least the highest of them. That keeps the field a lower bound in every case,
    which is what it always was when it was right.
    """
    best = max((r.get("chapters") or 0 for r in rows), default=0)
    return max(best, stated or 0, stated_chapter_number(latest_ep))


def collapsed_length(chs):
    """How many chapters a list of entries represents, with a split instalment counted once.

    GigaViewer publishes 第23話 わたしのままで as (1)(2)(3), three entries on one day, and counting
    entries reported works as longer than their own numbering says they are. `importdates.PART` is
    the same regex doing the same job for date detection, where counting entries made a monthly
    update look like a back-catalogue import. The fact was produced once and used in one place (§3).

    An entry with no title counts as itself, so a run of untitled chapters cannot collapse into one.
    Only a shared base title collapses, which is the case this is about.
    """
    bases, untitled = set(), 0
    for ch in chs:
        base = importdates.PART.sub("", str(ch.get("title") or ch.get("ep") or "")).strip()
        if base:
            bases.add(base)
        else:
            untitled += 1
    return len(bases) + untitled


def best_known_length(rows):
    """The most chapters any one source holds for a work.

    Not a sum, because every source describes the same story and adding them reported 135 chapters
    for a 121-chapter work. Not the state-deciding row's count either, which is what this used to
    take: that row is chosen for its DATES, and the source with the best dates is often not the
    source with the most chapters. ナメられたくないナメカワさん is the case the sort's own comment
    cites, where コミックDAYS watched the run end in 2022 and 一迅プラス holds all 77 chapters, and
    the work was published as 29 chapters long. How long the work is and when it last published are
    two questions, and one row cannot be trusted to answer both.
    """
    return max((r.get("chapters") or 0 for r in rows), default=0)


def can_testify(chapters):
    """Whether one source file has seen enough of a work to say its dates were observed.

    Import stamps are detected per file, by looking for a run of instalments sharing a timestamp.
    A file holding one chapter of a work cannot see a run, so it never reports one, and reading
    that inability as an observation is how a thin source overturns a stamp two fuller sources
    agree on. sitemap-magapoke.yaml holds a single chapter of ハロー、メランコリック！ at 2021-11-11
    and did exactly that, leaving the work `dormant` off the day 講談社 loaded it onto the platform,
    with 【track1】 shown as its newest episode.

    More than one distinct date is the test. A single date across every chapter a file holds is the
    import signature itself, not evidence against it.
    """
    return len({str(c.get("updated") or "")[:10] for c in (chapters or [])
                if c.get("updated")}) > 1


_WORK_ALIASES = None

# Every title a source wrote with a reading gloss in it, keyed on the name it leaves behind. The
# gloss is visible at ingest and nowhere afterwards, and the reading half of the rule runs later,
# in the naming autopilot, so `work_alias` writes down what it took out. `glossed_titles` is the
# one reader; `names/gloss.py` turns a pair into a reading.
_GLOSSED = {}


def glossed_titles():
    """`{name: the string a source wrote it as}` for every gloss taken out of a title this run."""
    return dict(_GLOSSED)


def work_alias(title):
    """The canonical title where two sources write one work differently.

    TWO THINGS DECIDE IT, and only one of them can be a rule. A reading gloss printed inside a
    title is a class with a shape: `恋する小惑星（アステロイド）` is 恋する小惑星, and
    `names/gloss.py` holds the rule and the counter-case it turns on. Everything else is curated in
    `data/work-aliases.yaml`, because nothing in a title says whether a bracketed suffix marks
    another edition of this work or a different work: 【タテスク】 is the first and 【読み切り版】
    is the second.

    The gloss comes off first, so a curated entry is written against the name and not against one
    source's spelling of it. Curated matching is after `norm_work`, so a source need not reproduce
    width or punctuation to be recognised.
    """
    global _WORK_ALIASES                                                    # noqa: PLW0603
    if _WORK_ALIASES is None:
        p = pathlib.Path("data/work-aliases.yaml")
        rows = (yaml.safe_load(p.read_text()) or {}).get("aliases") or [] if p.exists() else []
        _WORK_ALIASES = {norm_work(r["variant"]): r["canonical"] for r in rows
                         if r.get("variant") and r.get("canonical")}
    title = str(title or "")
    named = _gloss.plain(title)
    if named and named != title:
        _GLOSSED.setdefault(named, title)
        title = named
    return _WORK_ALIASES.get(norm_work(title), title)


def catalogued_title(title):
    """A print record's title area with the work's own name in the Japanese slot.

    The web path aliases a work's title where it reads one and this is the same call on the print
    path's record, which reaches `works.json`, `index.json` and the corpus statement in
    `titles.json`. Those are three surfaces a reader meets, and until this they carried
    `恋する小惑星 (アステロイド)` while the serialisation row for the same work carried the name
    (STANDING-INSTRUCTIONS §13: check every surface separately).

    `yomi` is left alone. Where MADB states one for a glossed title it has already applied the
    gloss, so it agrees with the shortened name rather than with the string it was cut from.
    """
    ja = (title or {}).get("ja")
    named = work_alias(ja) if ja else ja
    return title if named == ja else {**title, "ja": named}


# Kana and kanji. A string with none of these needs no reading: it is already Latin.
# ASKED OF `facts/script`, which owns which writing system a string is in.
JAPANESE_SCRIPT = _script._SCRIPT

# Characters that have to be READ before they can be romanised. Kana are not among
# them: hiragana to katakana is a transcription and cannot be a wrong guess.
NEEDS_READING = re.compile(r"[一-鿿々A-Za-zＡ-Ｚａ-ｚ0-9０-９]")


def _shop_address(rec):
    """Where a reader can buy this edition, or None.

    ONLY A RETAILER'S ADDRESS COUNTS. `marketing_label_basis` carries the page a label was read
    from, and for a record built from the national bibliography that page IS the bibliography:
    mediaarts-db.artmuseums.go.jp. Taking the field without asking whose it was put the national
    database under a heading reading "Sold at" on 824 works, which is both wrong and the kind of
    wrong a reader would believe.
    """
    basis = rec.get("marketing_label_basis") or {}
    return basis.get("url") if basis.get("source") == "bookwalker" else None


def _print_block(rec):
    """One work's book run, as the works list carries it under a row's `print`.

    ONE PLACE THE BLOCK IS BUILT. Three copies of this literal stood in the works-list assembly, so
    a field added for a reader reached whichever of the three the author happened to be looking at
    and the other two rows silently lacked it. STANDING-INSTRUCTIONS §3 covers this: the fact with
    three producers is the SHAPE of the block.

    WHO PUBLISHED AND WHO DELIVERED, kept apart all the way to the reader. MADB writes a
    distributor as `[発売]講談社` in the same field as the publisher, `adapters/madb/extract.py`
    reads the role out of the bracket, and both fields travel from there. `publisher_basis` says
    why the publisher is missing where it is, because an empty name and an unanswered question look
    identical on a page.

    `first` IS A PRINTING AND A DELIVERY DATE DOES NOT GO IN IT. The interface labels this field
    初刊, "first printed", and 1,297 works dated from a shop's 配信開始日 would have read as printed
    editions with a date the printer never set. The delivery date travels as `delivered_from` and
    carries its own label, which is the same separation 発売日 and 奥付 got: two facts about one
    book and not one fact at two precisions.
    """
    _fp = rec.get("first_publication") or {}
    _delivered = _fp.get("date_event") == delivery.EVENT
    return {
        "work_id": rec["work_id"],
        # WHERE TO BUY IT, which the record has carried all along. A retailer is Tier C and its
        # shelf is never a marketing_label (§4); a link to the shop selling the book says only that
        # the shop sells it, which is what a reader following it wants. Absent on a record from the
        # bibliography, which knows the edition and not the shop.
        "shop_url": _shop_address(rec),
        "volumes": rec.get("volume_count"),
        "publisher": rec.get("publisher"),
        **({"publisher_basis": rec["publisher_basis"]} if rec.get("publisher_basis") else {}),
        **({"distributor": rec["distributor"]} if rec.get("distributor") else {}),
        "imprint": rec.get("imprint"),
        "first": None if _delivered else _fp.get("date"),
        **({"delivered_from": _fp.get("date")} if _delivered else {}),
        "last": rec.get("last_published"),
        "label": rec.get("marketing_label"),
    }


# WHERE EACH SHOP'S YURI SHELF IS CAPTURED. The key is the name `admitted_by` writes for the
# comparator and the value is the capture that read it. Declared rather than inferred, because the
# two captures spell the shop differently in their own `source:` field, `bookwalker.jp` in one and
# `cmoa` in the other, so a host guessed out of either would be a third spelling of one shop.
SHELF_CAPTURES = {"bookwalker.jp": "data/queue/bookwalker-yuri.yaml",
                  "cmoa.jp": "data/queue/cmoa-yuri.yaml"}


def shelf_page_url(listing_url, page):
    """One page of a shop's shelf listing, or the listing unchanged where no page is known.

    The captures state a listing address with `page=1` on it and then record which page each work
    was read from, so the address a row cites is built by putting that number back rather than by
    composing a URL from parts. A page the capture did not state leaves the address alone: a
    citation to page 1 of a shelf the work is not on is the fault this whole change is about.
    """
    base = str(listing_url or "").strip()
    if not base or not page:
        return base or None
    parts = urlparse.urlsplit(base)
    query = [(k, v) for k, v in urlparse.parse_qsl(parts.query) if k != "page"]
    query.append(("page", str(int(page))))
    return urlparse.urlunsplit(parts._replace(query=urlparse.urlencode(query)))


def shelf_citations(captures=None):
    """Where each shop's yuri shelf can be read, and which page of it a work was found on.

    `{comparator: {"url": the shelf, "pages": {shop id: (page number, that page's address)}}}`.

    WHY THE SHELF AND NOT THE BOOK. DEFINITIONS §2 admits a work because a licensed retailer filed
    it under 百合, and the shelf is the only page that shows the filing. A row citing the shop's
    page for the book sends a reader to check a claim that page does not make, which is worse than
    citing nothing: it invites the check and then fails it. One operator followed such a citation,
    found no 百合 anywhere on the series page it led to, and concluded the entry was wrong.

    THE CAPTURE HEADER'S CLAIM IS NOT LEANED ON. `bookwalker-yuri.yaml` says the genre is
    "presented on every work page", which would make the book's page a second place to check. It is
    a statement about WORK pages, and 646 of the addresses we hold are SERIES pages, which it never
    covered. It is also a year-old reading of a shop that redraws its pages at will. So the shelf
    is cited because it is where the capture read the claim, which is a fact about our own act.
    """
    out = {}
    for comparator, path in sorted((captures or SHELF_CAPTURES).items()):
        p = pathlib.Path(path)
        if not p.exists():
            continue
        doc = yaml.safe_load(p.read_text()) or {}
        shelf = str(doc.get("source_url") or "").strip()
        if not shelf:
            continue
        listings = {str(k): str((v or {}).get("url") or "")
                    for k, v in (doc.get("listings") or {}).items()}
        pages = {}
        for item in doc.get("items") or []:
            key, page = str(item.get("id") or ""), item.get("page")
            base = listings.get(str(item.get("listing") or "")) or shelf
            if key and page:
                pages[key] = (int(page), shelf_page_url(base, page))
        out[comparator] = {"url": shelf, "pages": pages}
    return out


def cite_shelf(entry, shelves, shop_id=""):
    """A comparator entry with the address its claim can be checked at.

    `admitted_by` names the shop and the shelf and states no address at all, so the shelf rows on a
    work page carried no citation and the only BOOK☆WALKER link beside them pointed at the book.
    This puts the shelf on the entry; `classify/credence.py` turns it into the row.

    NOTHING IS INVENTED. A comparator with no capture here keeps the entry it had, and a work the
    capture states no page for cites the shelf without one. The alternative in both cases is an
    address nobody read.
    """
    shelf = shelves.get(str(entry.get("comparator") or "").strip().lower())
    if not shelf:
        return entry
    page, url = shelf["pages"].get(str(shop_id or ""), (None, shelf["url"]))
    cited = dict(entry, url=url)
    if page:
        cited["page"] = page
    return cited


def _record_address(rec, name):
    """The page THIS source holds the work on, or None.

    Same question as `_shop_address` and the same trap. Every record carries several addresses and
    they belong to different parties: the bibliography's catalogue page, the shop's product page,
    and whatever page a label was read from. A row saying "read from X on this date" has to point
    at X's page, so each source is asked for its own field by name rather than for whichever URL
    the record happens to hold.

    openBD is deliberately absent. It answers over an API keyed by ISBN and publishes no page for
    a reader to open, so it gets a row with no address instead of a link to somebody else's.
    """
    if name == "bookwalker":
        return rec.get("shop_url")
    if name in ("madb", "madb-title"):
        basis = rec.get("marketing_label_basis") or {}
        return rec.get("madb_url") or (basis.get("url") if basis.get("source") == "madb" else None)
    return None


# Every capture of work-level addresses, whichever platform it was read from. Globbed rather than
# named, because there are four of them today, one per shape the platforms write, and a fifth
# arriving would otherwise be read by identity.py and not by this. `record_type` is what selects
# them: `address-moved.yaml` sits under the same prefix and attaches ANOTHER CHAPTER address, which
# is the one thing this field must never carry.
WORK_ADDRESS_CAPTURES = "data/queue/address-*.yaml"
WORK_ADDRESS_RECORD = "stable_address"


def work_level_addresses(docs):
    """`{chapter address: the work's own address}` over the captures that read them.

    TWO SHAPES, BECAUSE THE PLATFORMS DIFFER. Every GigaViewer host serves `/atom/series/<id>`, and
    337 of the 506 rows also have `/series/<id>/first_episode`, the address the platform itself puts
    behind a series on its own listings. 一迅プラス, コミックガルド, MAGCOMI and webアクション serve
    no route for the second, and two of them answer it with HTTP 200 carrying their front page, so
    the reader address is taken only where the capture established that the page names the series.

    The reader address is preferred where there is one and the feed stands everywhere else. Both are
    anchors the registry already holds, so either resolves to the identifier the work has.
    """
    out = {}
    for doc in docs:
        if str((doc or {}).get("record_type") or "") != WORK_ADDRESS_RECORD:
            continue
        for join in (doc.get("joins") or []):
            url = str(join.get("url") or "")
            found = str(join.get("anchor") or "").split("web:", 1)[-1]
            if not url or not found:
                continue
            if url not in out or "/atom/" not in found:
                out[url] = found
    return out


def state_claim_rows(rows):
    """What each platform says about its own serialisation, one row per platform that says it.

    THE SAME SHAPE AS AN EVIDENCE ROW, and for the same reason: who spoke, what they said, and when
    it was read. `state_basis` used to carry this welded into a sentence about our own coverage:
    "no chapter for 2 days in what we hold, but the platform still marks the serialisation as
    running". That is one claim about the WORLD and one about THIS DATABASE in a paragraph the page
    could only print whole. `age_days` already carries our half as a number; this carries the
    platform's half as a row, so both can be rendered like every other fact on the page.

    `says` is our reading and `term` is the platform's own value, kept apart because カドコミ
    answers `finished` in English where comici answers 完結 and flattening the two would hide that
    they are separate sources agreeing.

    A completed claim sorts above a running one, so a work whose platforms disagree leads with the
    stronger statement rather than with whichever row happened to be built first.
    """
    out = []
    for row in rows:
        claim = row.get("state_claim") or {}
        if not claim.get("says"):
            continue
        out.append({"source": row.get("platform"), "says": claim["says"],
                    "term": claim.get("term") or None,
                    "read": row.get("retrieved") or None,
                    **({"url": row["url"]} if row.get("url") else {})})
    return sorted(out, key=lambda x: (x["says"] != "completed", str(x["source"] or "")))


def series_address(row, addresses):
    """The work's own address for a row addressed at one of its chapters, or None.

    WHY A ROW NEEDS ONE. `identity.py` anchors a work on its row's address, and a row's address is
    its newest chapter's, so on a GigaViewer platform a work that publishes looks like a work never
    seen before. `identity.stable_url` closes the addresses that carry the work's own in front of
    them; these are the 507 that carry nothing but a chapter id.

    NOTHING IS DERIVED FROM THE CHAPTER ADDRESS. It is either an address somebody read or the feed
    the row is already holding, and a row with neither says so by carrying no field.
    """
    url = str(row.get("url") or "")
    found = addresses.get(url) or row.get("feed_url") or None
    return found if found and found != identity.stable_url(url) else None


def credits_en(raw, exact, folded, fold):
    """One rendering for an author field naming several people, or None.

    THE COMPOSITION ITSELF IS IN adapters/names/credits.py, because two views need it and each
    solving it separately is how the works list and the updates feed came to disagree: the series
    rows composed on ` / ` and the release rows never composed at all, so the same four people
    rendered in English in one tab and in Japanese in the next. This is the store lookup and
    nothing else.

    THE FULLER RECORD WINS, which is the same rule the title join a few hundred lines below
    applies. The same person reaches us spelled two ways and the store holds a record for each,
    one curated and one carrying only an automatic reading.
    """
    def lookup(part):
        cands = [x for x in (exact.get(part), folded.get(fold(part))) if x]
        return max(cands, key=_fullness) if cands else None

    return _credits.compose(raw, lookup)


def rebuttals():
    """{work id: visibility} from data/rebuttals.yaml, the operator's answer to a §2 admission.

    NOTHING IS DELETED HERE. §2 admits a work a comparator lists and calls that presumptive and
    rebuttable, and this is the rebuttal. A work named here keeps its record, its identifier and its
    page, and stops appearing in a default listing. The reasoning is that the two errors are not the
    same size: a work wrongly present is visible, citable and can be rebutted by anyone who looks,
    while a work wrongly absent is invisible and the reader who needed it never learns it existed.
    Leaving the address working keeps the cheap error cheap; taking it out of the listing keeps a
    doubtful entry from reading as an ordinary one.

    `out` is a source disagreeing with a source, which §4 can settle. `marginal` is the operator
    declining to decide, which DEFINITIONS §9 says is where this database stops rather than a gap in
    it. The interface separates them because they mean different things, and neither is deletion.
    """
    f = pathlib.Path("data/rebuttals.yaml")
    if not f.exists():
        return {}
    doc = yaml.safe_load(f.read_text()) or {}
    seen = {}
    for group in ("rebutted", "upheld"):
        for row in (doc.get(group) or []):
            wid, how = row.get("work"), row.get("disposition")
            if wid and how in ("out", "marginal"):
                seen[wid] = "rebutted" if how == "out" else "marginal"
    return seen


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
    try:
        import provenance as _prov
    except Exception:
        _prov = None
    try:
        from facts import division as _boundary
    except Exception:
        _boundary = None

    # WHICH RECORD A NAME IS, so the interface can link one. `feed/names.json` is keyed by the
    # folded string and carried the reading, the romanisations and the ruby; it carried no
    # identifier, so app.js could render a credit and could not point at it. That is the whole of
    # what stood between a registry of 2,238 minted addresses and a page a reader can open.
    #
    # ONE FOLD, SHARED, WHICH IS WHY THE LOOKUP CANNOT MISS. `credit_identity.credit_key` and
    # `publisher_identity.house_key` both normalise NFKC and drop spaces, which is `names.key.fold`,
    # which is what this file keys the map on. Written down in three docstrings and asserted by
    # `every shipped credit has an identifier`, because a map holding an id the anchors do not
    # answer for is a link to nowhere.
    _cred_ids = registry_index("credits")

    def render(k_ja, rec, is_person=False):
        out = {}
        rd = rec.get("reading")
        # FURIGANA OVER A PERSON'S NAME HAS TO REST ON SOMETHING. An analyser is at its weakest on
        # pen names and it does not decline: 古川楊也 is stored ホシノ カツラ, which is a different
        # person's name, and it was being printed over theirs. A title read wrongly is an error; a
        # name read wrongly misnames somebody, so the two do not get the same benefit of the doubt.
        #
        # A reading a source states, or that a person researched and cited, gets furigana. A
        # machine's guess does not, and nothing replaces it: the name renders as the Japanese it
        # is, which is what a reader would see in print.
        #
        # The FURIGANA only. The romanisation stays, because it is a different claim in a different
        # place: Latin letters beside a name are how a reader without Japanese finds the person at
        # all, and a romanisation is labelled as ours already. Suppressing both took 400 author
        # names out of English rendering entirely, which trades one wrong for a worse one.
        _guessed_person = is_person and rec.get("reading_basis") in ("analyser", "back-converted")
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
                # The reading keeps its spaces. Where the surface is spaced the same way they are
                # the boundary, and align() strips them itself when they are not.
                got = _kana.align(k_ja, rd)
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
            if sp and any(x[1] for x in sp) and not _guessed_person:
                out["ruby"] = sp
            # Personal names take particles=False — と in a name is 都 or 斗, never the particle.
            # latinise here too. It was applied to `en` and not to the romanisations, so a title
            # whose reading romanised cleanly could still ship its Japanese punctuation — ｜ in
            # コミックオギャー)｜… survived every pass because this one output skipped the step.
            out["romaji"] = _romanisation.styles(
                rd, _romanisation.PERSON if is_person else _romanisation.TITLE)
            # A NAME ROMANISED AS ONE WORD BECAUSE NOTHING SAYS WHERE IT DIVIDES. 太陽まりい is
            # filed タイヨウマリイ by the media-arts catalogue, which is correct and closed up, so
            # the romanisation came out `Taiyōmarii` and the person is 太陽 まりい.
            #
            # THE GLUED FORM IS THE RIGHT FALLBACK AND THE WRONG THING TO SAY NOTHING ABOUT.
            # NAMES-PLAN records two attempts at deriving a division from the characters and why
            # both were refused: the surface of a Japanese name carries no boundary, and guessing
            # one publishes a wrong claim about a real person under their own work. So the glued
            # form stands, and the flag is what stops it standing as though it were settled. The
            # asymmetry is the same one §5d turns on: a Japanese reader has the name itself, and an
            # English reader has this string and nothing else.
            #
            # PEOPLE ONLY. A title is not divided into a family name and a given name and a run-on
            # romanisation of one says nothing about anybody.
            if is_person and _boundary and not _boundary.cuts(rd):
                out["undivided"] = True
            # AND A DIVISION THAT RESTS ON AN ANONYMOUS EDIT SAYS SO. アカイマルボロウ is a kana
            # credit whose sounds are its own surface, so nothing about the reading is in doubt and
            # the `[?]` would be false; what it took from a Wikidata record is the SPACE. Eight
            # people were divided that way and rendered with no mark of any kind, because the doubt
            # sat on the donor's record and the interface only ever sees this one.
            #
            # THE 68 WHOSE OWN READING IS WIKIDATA'S ARE NOT HERE, and that is not an oversight.
            # Their basis is `community-printed`, they already carry `unverified`, and a second mark
            # on the same claim is the flood NAMES-PLAN §5d narrows every mark to avoid. Since the
            # owner's correction of 2026-08-09 that one mark is the floor's own, which says the
            # Latin a reader is looking at is ours and covers the space along with the sounds.
            # `boundary.fill` writes the field for a division it LENT and for nothing else.
            elif is_person and rec.get("reading_boundary_basis"):
                out["division_basis"] = rec["reading_boundary_basis"]
        # A FIFTH CLAIM, AND THE ONLY ONE NO RULE CAN FIND. Where the kana are themselves a
        # transliteration, romanising them takes a reader FURTHER from the name than the Japanese
        # did: ステファン・セジク comes out `Sutefan Sejiku` and the person is Stjepan Šejić. Nothing
        # about a string says this, since katakana pen names are ordinary, so it is recorded per
        # name in curated.yaml and shipped here for the interface to say so.
        if rec.get("transliterates"):
            out["transliterates"] = rec["transliterates"]
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
        # THE PAGE THE READING WAS READ FROM. The store has recorded it since the first sourced
        # pass and nothing ever shipped it, so 771 author readings held an address anyone could
        # open and no reader was offered one. `reading_basis` said a source stated the reading and
        # then declined to say which, which is an assertion with the evidence withheld.
        #
        # `provenance.cite` decides what may be shown and is the only thing asked. It answers None
        # for a kana surface and for an analyser guess, because neither has a document behind it,
        # and §6 keeps our own machinery off the page: the unverified mark already says what a
        # reader can act on there. What is left is a claim about the NAME, of the same kind as the
        # `basis` a classification carries under DEFINITIONS §5, and a Japanese-literate reader can
        # follow it to the source and judge it.
        _cited = _prov.cite(rec) if _prov else None
        if _cited:
            out["reading_cite"] = _cited
        # AND WHERE AN ENGLISH NAME CAME FROM, which nothing shipped at all. `basis` said a title's
        # English is the work's own or a licensor's, both of which are shown UNMARKED because they
        # are not our claim, and then declined to say whose. That is the §1 failure in the place it
        # matters most: an unmarked name reads as authoritative, so the one form a reader has no
        # reason to doubt was the one carrying no evidence. 286 of them, with the licensor's page
        # sitting in `data/names/curated.yaml` since the day each was curated.
        #
        # SAME PRODUCER AS THE READING'S. `provenance.cite` took a claim argument from the day it
        # was written and nothing ever passed one; a second function assembling the same five
        # fields for the other claim is the shape §3 counts seven shipped bugs from. It answers
        # None for `translated` and `romaji`, because those are ours and the interface already
        # marks them ours, and None for a title already in Latin, whose own name is the English one.
        _en_cited = _prov.cite(rec, "en") if _prov else None
        if _en_cited:
            out["en_cite"] = _en_cited
        # False is meaningful and must survive; missing is not the same as verified.
        # A researched reading is exempt: somebody looked the word up and said why, which is
        # exactly what the mark is asking for, so marking it would ask for work already done.
        # A SURFACE ALREADY IN KANA WAS NOT READ, SO NOTHING WAS GUESSED. よつば◎ますみ。 carried
        # the mark because its reading came from the analyser, but ヨツバ ◎ マスミ。 is that name
        # transcribed, and hiragana to katakana is mechanical. The mark says the reading might be
        # wrong, and here there is no reading to be wrong about. 331 records were marked this way.
        #
        # KANJI, LATIN AND DIGITS ALL DISQUALIFY. Each of them has to be READ: タイザン5 could end
        # ゴ or ファイブ, and that is a real guess, so it keeps its mark.
        # AND ORDINARY VOCABULARY IS NOT A GUESS EITHER, ruled by the project owner 2026-08-10:
        # for fundamental kanji, the absence of special information is evidence that they have
        # their obvious readings, in a title. 私 is ワタシ, 体 is カラダ, 風俗 is フウゾク and 百合
        # is ユリ, and the note stored on each of those records justified its mark by saying
        # analysers are weakest on pen names and coinages, which those are not. So the mark is
        # drawn where the analyser says it met a proper noun, a word its dictionary does not hold,
        # or a compound it had to read a character at a time.
        #
        # `reading_ordinary` IS THE ONE PRODUCER OF THAT ANSWER, written by
        # adapters/names/analyser_vocabulary.py on every build, because deciding it needs the
        # analyser and this function runs with no tokeniser and must work without one installed.
        # The pass removes the field from any record that leaves the `analyser` basis, so a title
        # a source later settles cannot carry a stale one.
        _mechanical = k_ja and not NEEDS_READING.search(str(k_ja))
        _ordinary = rec.get("reading_ordinary") and rec.get("reading_basis") == "analyser"
        if (rec.get("verified") is False and not _mechanical and not _ordinary
                and rec.get("reading_basis") not in ("researched", "stated")):
            out["unverified"] = True
        # A reading assembled character by character because nothing could read the word. Weaker
        # than an ordinary guess and marked separately: 抱き寝ーター came out カカエきネーター, where
        # 抱き is ダキ — the isolated reading of a character is often not its reading in a compound.
        if rec.get("reading_uncertain"):
            out["uncertain"] = True
        return out or None

    # PUBLISHERS ARE THE THIRD KIND, and they were the last name the site fetched for itself.
    # data/names/publishers.yaml holds them exactly as the other two are held, so the only thing
    # that made them different was where the map was written: adapters/names/publishers.py ran from
    # deploy.sh and emitted a file of its own. A second producer of one fact, and one that ran
    # after the build had already declared itself finished.
    got = {}
    for kind in ("authors", "titles", "publishers"):
        f = pathlib.Path("data/names") / f"{kind}.yaml"
        if not f.exists():
            got[kind] = {}
            continue
        d = (yaml.safe_load(f.read_text()) or {}).get("names") or {}
        # Only the author map is keyed on a string an identifier was minted for. The publisher
        # map ships under the CORPUS's spellings rather than the store's, so its identifiers are
        # joined in `publisher_map`, where those keys exist.
        ids = _cred_ids if kind == "authors" else {}
        prefix = "credit:"
        got[kind] = {k: v for k, v in
                     ((k, _rendered(kind, k, v, render, ids, prefix)) for k, v in d.items()) if v}
    return got.get("authors", {}), got.get("titles", {}), got.get("publishers", {})


def registry_index(which):
    """`{anchor: id}` for a minted registry, or `{}` where there is none yet.

    ONE READER OF A REGISTRY FILE, asked by name. `identity.index` is what resolves an anchor,
    including through a merge, so a retired spelling reaches the identifier that survived it and a
    published address keeps working. Everything here goes through that function rather than reading
    `anchors` itself, which is what would let a page and a forwarder disagree about where a merged
    record went.
    """
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters"))
        from facts import identity as _ident
        if which == "credits":
            import credit_identity as _mod
        else:
            import publisher_identity as _mod
        return _ident.index(_mod.load(f"data/identity/{which}.yaml")[0])
    except Exception as _e:                                                     # noqa: BLE001
        print(f"names           : no {which} registry to link ({_e})")
        return {}


def _rendered(kind, k, rec, render, ids=None, prefix=""):
    """One store record as the interface gets it, or None where it should not answer a lookup.

    A CREDIT THAT IS NOT A PERSON IS STILL A CREDIT. 円谷プロダクション is the whole byline on the
    SSSS.GRIDMAN anthology and 「真夜中ぱんチ」製作委員会 is one of three on 真夜中ぱんチ, so both
    render. What they stop doing is passing as a personal name: `is_person` withholds furigana from
    a reading a machine guessed, because a pen name is what an analyser is worst at, and it lower
    cases nothing because a personal name holds no particle. Neither applies to a company, whose
    name is made of ordinary words. See adapters/names/entities.py.

    NOTATION IS THE ONE THAT ANSWERS NOTHING. `はいむらきよたか(キャラクターデザイン)` is a person
    with a role welded on and the store holds the person separately, so a lookup on the raw field
    should reach the person. It did not: the raw string is tried before `credits.compose` and won,
    which is how `Ishida Kana ( Kyarakutā Dezain )` came to sit in names.json with a role label
    romanised as part of somebody's name. The record stays in the store, marked; it is the RENDERING
    that is withheld, and `credits that carry their own cataloguing` counts what is withheld so the
    filtering is observable (STANDING-INSTRUCTIONS §13).
    """
    entity = (rec or {}).get("entity") if kind == "authors" else None
    if entity == "notation":
        return None
    out = render(k, rec, is_person=(kind == "authors" and not entity))
    # THE ADDRESS OF THE RECORD THIS NAME IS. Attached here rather than in `render`, because it is
    # not a rendering: it does not depend on the reader's language, style or name order, and it is
    # the same string in every mode. A title gets none, because a work's identifier is already on
    # its own row and the page it opens is built from that row.
    #
    # A NAME WITH NO IDENTIFIER IS A STATE AND NOT A GAP. The registry is minted from the works
    # list, so the store legitimately holds records nothing credits: a second spelling a ruling
    # attached, a publisher name in the store that no print row carries. Those render as before and
    # are simply not links.
    if out and ids:
        got = ids.get(prefix + _namekey.fold(k))
        if got:
            out["id"] = got
    return out


def credit_page_data(rows):
    """Everything a credit's page shows that no other shipped file holds.

    WHAT IT ANSWERS, and why the interface cannot. "What else is this person named on" needs the
    credit field SPLIT, which is `inputs.split_credits_detail`'s job and exists only in Python;
    doing it in the browser would be a second splitter, and the two would disagree about who a
    work is by. So the edges ship, derived by the registry module that already owns them.

    WHAT SHAPE OF PAGE EACH RECORD MAY HAVE. 20 of these credits are not people. 円谷プロダクション
    is a company, 「真夜中ぱんチ」製作委員会 a committee, and 電撃G'sマガジン is a magazine, which
    DEFINITIONS treats as a place where yuri is published rather than as a party to a work. `shape`
    carries that, so the renderer can head a page with what the credit is instead of assuming a
    person and printing a reading, a name order and a romanisation for a limited company.

    `homophones` IS THE INFORMATION HUNG BESIDE A CREDIT, which is what the owner's ruling means by
    ancillary: seven pairs share a reading and were examined and kept apart, and a page for either
    should be able to say the other exists. It is never a merge and never replaces one with the
    other.

    A RETIRED IDENTIFIER SHIPS TOO, in `merged`, for the reason the works list ships one: a page
    asked for a retired id has to land on the record that survived it rather than on nothing.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters"))
    import credit_identity as _cid

    entries, doc = _cid.load("data/identity/credits.yaml")
    edges = {}
    for f in ["data/identity/credit-works.yaml"]:
        if pathlib.Path(f).exists():
            for row in (yaml.safe_load(pathlib.Path(f).read_text()) or {}).get("credits") or []:
                edges[str(row.get("id"))] = row.get("works") or []
    # WHICH WORKS THE READER MAY BE SHOWN, taken from the rows that ship rather than from the edge
    # file. A work withheld on content grounds leaves the works list and its identifier stops being
    # served, so an edge naming it would put a withdrawn title on a person's page. That is
    # STANDING-INSTRUCTIONS §13's rule about checking every surface, and this is a new surface.
    known = {str(r.get("id")) for r in rows if r.get("id")}
    homophones = {}
    for pair in (doc or {}).get("homophones") or []:
        for c in pair.get("credits") or []:
            if not c.get("id"):
                continue
            homophones.setdefault(str(c["id"]), []).extend(
                {"id": str(o.get("id")), "credit": o.get("credit"), "reading": pair.get("reading"),
                 "basis": pair.get("basis")}
                for o in pair.get("credits") or []
                if o.get("id") and str(o["id"]) != str(c["id"]))
    out = {}
    for e in entries:
        cid = str(e.get("id") or "")
        if not cid or e.get("merged_into"):
            continue
        works = [{"id": str(w.get("id")), **({"roles": list(w["roles"])} if w.get("roles") else {})}
                 for w in edges.get(cid) or [] if str(w.get("id")) in known]
        fact = {"credit": e.get("title"), "shape": _cid.shape_of(e.get("kind")),
                "works": works}
        if e.get("kind"):
            fact["kind"] = e["kind"]
        if homophones.get(cid):
            fact["homophones"] = homophones[cid]
        out[cid] = fact
    return {"generated": str(datetime.date.today()),
            "note": "One record per credit, with the works it is named on and the role on each "
                    "edge. Addresses are opaque and minted: a credit read three ways in a day "
                    "would have broken a name-shaped one twice. Fetched only when a credit page "
                    "is opened.",
            "count": len(out), "credits": out,
            # A CHAIN IS NOT FOLLOWED HERE. `identity.index` already resolves an anchor
            # through however many merges, and the interface follows this map the way it follows
            # the works one, so A into B into C lands on C in the browser exactly as it does in
            # the forwarder. Shipping the raw pairs keeps the two agreeing.
            "merged": _cid.retired(entries)}


def publisher_page_data(rows):
    """Everything a house's page shows: its lines, the years each spelling covers, and its works.

    WHAT A PUBLISHER PAGE SHOWS THAT NOTHING ELSE CAN, which is the reason it exists at all: which
    of a house's imprints are yuri lines. 百合姫コミックス carries 354 rows and a house with one
    book somebody shelved as yuri carries one, and that difference is visible only when the lines
    are counted side by side under the company that runs them.

    ONE PRODUCER. `publisher_identity.houses` assembles it from `imprints.census`, which is the
    only thing that decides which line a catalogued string names. The interface renders what comes
    out and derives no span of its own, so the page and the registry report cannot disagree about
    when a spelling was in use.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters"))
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters" / "names"))
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters" / "facts"))
    import imprint as _imp
    import publisher_identity as _phid

    entries, _doc = _phid.load("data/identity/publishers.yaml")
    facts = _phid.houses(rows, _imp.load(pathlib.Path("data/names/imprints.yaml")), entries)
    return {"generated": str(datetime.date.today()),
            "note": "One record per publishing house, holding the imprint lines it runs with the "
                    "spellings each line is catalogued under and the years those cover. Publishers "
                    "and distributors share one namespace: the seat is on the edge to the book.",
            "count": len(facts), "publishers": facts,
            "merged": _phid.retired(entries)}


def publisher_map(names, people, rows):
    """`{key: {en, basis}}` for the interface, keyed by the catalogued string AND by the shown one.

    KEYED BOTH WAYS ON PURPOSE. The cataloguing around a name is stripped in two places, by
    `publisher_of` here and by `publisherOf` in app.js, and §3 says two implementations of one rule
    will drift. They cannot be merged, because one runs in a browser. What removes the cost of a
    drift is that the raw catalogued string answers too: a normaliser that misses something asks
    with a string this map still knows, instead of a publisher silently going back to Japanese.

    THE WHOLE OF THE RULE COMES FROM adapters/names/publishers.py, including which record answers
    for a string and what an answer looks like. This used to hold its own copy of the join while
    the module held another for the report and check.py's budget, which is three readings of one
    fact; the module's is the only one now. `people` is the author map, because a self-published
    work names its own author as its publisher and that name is already rendered once.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters" / "names"))
    import publishers as _pub
    out = _pub.render(names, people, _pub.corpus_names_from_rows(rows))
    # WHICH HOUSE A KEY IS, so a publisher on a work page can be a link to the house's own record.
    # Joined here because this map is keyed on the CORPUS's spellings, which is where the anchors
    # were minted from, and the store's keys are a different set.
    #
    # AN IMPRINT KEY GETS NONE, and it gets none by construction rather than by a test: identifiers
    # are minted from the publisher and distributor fields only, so a line's name answers nothing
    # here. That is the shape DEFINITIONS gives the two, a line belonging to the house that runs
    # it, and a page for 百合姫コミックス would be a second address competing with 一迅社's own.
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters"))
    import publisher_identity as _phid
    houses = registry_index("publishers")
    if houses:
        for k, fact in list(out.items()):
            got = houses.get(_phid.anchor(k) or "")
            if got and not fact.get("id"):
                # The fact is shared between the raw key and the shown one, so it is copied before
                # it is written to: two keys legitimately answer for one house, and one of them
                # naming a different one would be a link pointing away from the name beside it.
                out[k] = dict(fact, id=got)
        # A HOUSE WITH NO ENGLISH NAME IS STILL A HOUSE WITH AN ADDRESS. This map holds only names
        # something could render, which is the right rule for a rendering and the wrong one for a
        # link: 27 of the 164 houses have no English at all, so keying the identifier off a
        # rendering would have made exactly the smaller publishers unreachable, which is the half
        # of the corpus a publisher page is most informative about. An entry carrying an id and no
        # `en` renders as the Japanese it always did and is now something a reader can open.
        for _pr in rows:
            for _blk in (_pr.get("print") or ()):
                for _seat in ("publisher", "distributor"):
                    _nm = str(_blk.get(_seat) or "").strip()
                    _hid = houses.get(_phid.anchor(_nm) or "")
                    if not _hid:
                        continue
                    for _key in (_nm, _pub.publisher_of(_nm),
                                 _namekey.fold(_pub.publisher_of(_nm))):
                        if _key and _key not in out:
                            out[_key] = {"id": _hid}
    return out


def imprint_map(rows):
    """`{key: {id, name, parent}}` for the interface: which line a catalogued imprint string names.

    THE FIELD HELD ONE LINE AS MANY OBJECTS. 一迅社 runs a single yuri line and the print rows carry
    27 strings for it, because MADB, openBD and a retailer each transcribe one printed logotype
    differently and `adapters/madb/extract.py` stores whichever spelling the record it read stated.
    A publisher page over that field would give one line twenty entries, which is why this is the
    step in front of the pages and not part of them.

    ONE PRODUCER, AND IT IS NOT THIS FUNCTION. `adapters/facts/imprint` owns the registry and
    the matching; check.py measures the map this ships. `imprintOf` in app.js is the third reader of
    the same fact and is the one still deriving its own answer, which is what the shipped map is for.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters" / "names"))
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters" / "facts"))
    import imprint as _imp
    return _imp.shipped(rows, _imp.load(pathlib.Path("data/names/imprints.yaml")))



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
         # THE WEAKEST DATE THE DATABASE CARRIES, counted where the coverage facts live so that it
         # can be found again when a better source appears. `followup` is NOT a queue length:
         # `no-earlier-record-expected` is finished work under DEFINITIONS §6, since for a doujinshi
         # a platform sells the delivery day may be the only datable event in its history;
         # `unclassified` means the shop said nothing about the edition; and only
         # `earlier-edition-unsourced` names a row another source could answer.
         "delivery_dated": {**delivery.tally(series_rows),
                            "means": delivery.BASIS_NOTE[delivery.BASIS],
                            "followup_means": delivery.FOLLOWUP_NOTE},
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
    ap.add_argument("--checks", action="store_true",
                    help="run check.py --runtime at the end; skipped by default")
    ap.add_argument("--no-checks", action="store_true",
                    help="accepted and ignored; skipping is the default now")
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

    # A shop's claim about which volume ended a series, keyed by ISBN. Loaded before the work loop
    # because every volume asks the same question of it.
    FINAL_VOLUMES, FINISHED_BY_ISBN = {}, {}
    _fv = pathlib.Path("data/source/comparators/shop-final-volumes.yaml")
    if _fv.exists():
        _fvdoc = yaml.safe_load(_fv.read_text()) or {}
        for _fvrow in (_fvdoc.get("finals") or []):
            FINAL_VOLUMES[str(_fvrow.get("isbn") or "")] = {
                "source": _fvdoc.get("source"), "volumes": _fvrow.get("volumes"),
                "retrieved": str(_fvdoc.get("retrieved") or "")}
        # And whether the SERIES finished, which is a fact about the series and not about which of
        # its volumes we hold. A work joins on whichever ISBN it has.
        for _fnrow in (_fvdoc.get("finished") or []):
            for _fnisbn in (_fnrow.get("isbns") or []):
                FINISHED_BY_ISBN[str(_fnisbn)] = {"source": _fvdoc.get("source"),
                                                  "volumes": _fnrow.get("volumes"),
                                                  "retrieved": str(_fvdoc.get("retrieved") or "")}

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

    # WHO DREW A BOOK THE BIBLIOGRAPHY CREDITS TO NOBODY. 49 print works, almost all yuri
    # anthologies, carry `creator: ""` from MADB because the publisher registered the book under no
    # single author, and openBD's registration for them is empty too. adapters/bylines.py reads the
    # line-up off the publisher's own book page or the shop's and states it per work_id.
    #
    # KEYED ON THE ID, NOT THE TITLE. `author_of` further down carries the same fact for web works
    # and is keyed on a folded title, which is right there because a work reaches us under several
    # spellings. Here there is an id, and using it means a subtitle MADB writes and a shop does not
    # cannot silently attach one book's contributors to another.
    byline_credit = {}
    _bl = pathlib.Path("data/source/webpages/bylines.yaml")
    if _bl.exists():
        for _credit in ((yaml.safe_load(_bl.read_text()) or {}).get("print_works") or []):
            if _credit.get("work_id") and _credit.get("author"):
                byline_credit[_credit["work_id"]] = _credit["author"]

    undated_works = 0
    undated_by_basis = {}

    # Read once, ahead of the loop: 4,300 works would otherwise re-parse two capture files each.
    shelf_cites = shelf_citations()
    shelf_cited = shelf_paged = 0

    works, errors, warnings = [], [], []
    for wid, by_source in sorted(src.items()):
        # THE PRIMARY IS THE BEST RECORD THERE IS, which is not always the bibliography's. A work
        # from a retailer's shelf has no MADB record and never will: BOOK☆WALKER states no ISBN, so
        # nothing keyed on one can reach it. Refusing it here would have meant holding 2,093 fewer
        # works in order to keep a rule about which file the title came from.
        base = by_source.get("madb") or by_source.get("bookwalker")
        if not base:
            errors.append(f"{wid}: no primary record from a work source")
            continue
        ov = overlay.get(wid, {})

        w = {
            "work_id": wid,
            "title": catalogued_title(base["title"]),
            # `or` is not enough: a BOOK☆WALKER row whose authors list is empty comes through as
            # " / ", which is truthy and names nobody. See adapters/bylines.credited.
            "creator": (base.get("creator", "")
                        if _bylines.credited(base.get("creator", "")) else "")
                       or byline_credit.get(wid, ""),
            "publisher": base.get("publisher", ""),
            # Beside the publisher and never in it. The source layer reads the role out of MADB's
            # `[発売]講談社` and these two carry the halves it separated: who delivered the book,
            # and why nobody is named as having published it where that is the case.
            **({"distributor": base["distributor"]} if base.get("distributor") else {}),
            **({"publisher_basis": base["publisher_basis"]} if base.get("publisher_basis") else {}),
            "imprint": base.get("imprint", ""),
            "volume_count": base.get("volume_count", 0),
            "grouping": base.get("grouping"),
            "sources": sorted(by_source),
            # WHICH SOURCE HOLDS WHAT, AND WHEN IT WAS READ. `sources` above names them and
            # nothing said when any of them last spoke, so the work page could show a volume count
            # with no way to tell whether it was read this month or last year. One row per record,
            # each pointing at that source's own page rather than at whichever URL was nearest.
            "records": [{"source": _sname, "retrieved": str(_srec.get("retrieved") or "")[:10],
                         "url": _record_address(_srec, _sname)}
                        for _sname, _srec in sorted(by_source.items())],
        }

        # Volume-level merge: openBD confirms dates and may supply a cover reference.
        enrich = {v["isbn"]: v for v in (by_source.get("openbd", {}).get("volumes") or []) if v.get("isbn")}
        vols = []
        for v in base.get("volumes") or []:
            o = enrich.get(v.get("isbn", ""), {})
            m = {k: (str(v[k]) if k == "published" else v[k])
                 for k in ("madb_id", "number", "isbn", "published", "published_basis") if k in v}
            # WHAT THE SECOND CATALOGUE ADDS TO THIS VOLUME'S DATE. The test here was string
            # equality, so 2013-05 against 2013-05-24 read as a disagreement: the day went into
            # `published_openbd` and the reader went on seeing the month. That is one fact at two
            # precisions and the finer form is worth taking, while 2013-05 against 2013-06-02 is
            # two sources disagreeing and the held date stands. `isbndate.resolve` is the one
            # producer of that distinction; see its docstring for what each catalogue was measured
            # to be worth, including the publisher route that states a different date and not a
            # finer one.
            _vol_date, _vol_relation = isbndate.resolve(m.get("published"), o.get("published"))
            if _vol_relation in isbndate.TAKEN:
                m["published"] = _vol_date
                # A DATE THIS BUILD MOVED SAYS WHERE IT MOVED FROM. `published_basis` names the
                # catalogue in `cmoa_volumes.PREFERENCE`'s vocabulary and `published_source` names
                # the file, because `first_publication` below reports both and a volume dated from
                # the enrichment layer would otherwise be attributed to the bibliography.
                m["published_basis"] = o.get("published_basis") or "openbd-registration"
                m["published_source"] = "openbd"
            elif _vol_relation == isbndate.DISAGREES:
                # Keep the higher-priority value; record rather than discard the disagreement (§1).
                m["published_openbd"] = o["published"]
            if o.get("cover_url"):
                m["cover_url"] = o["cover_url"]
            # The enrichment row states whether openBD carried the book, and since 2026-08-06 a
            # row can exist because the other catalogue answered. Reading its own field rather
            # than the row's existence keeps "openBD has this" one fact with one producer.
            m["openbd"] = o.get("openbd") or ("present" if o else "absent")
            if volume_number(v) is not None:
                m["number_n"] = volume_number(v)
            vols.append(m)
        w["volumes"] = vols
        # THE SERIES FINISHED, ON A SHOP'S SAY-SO. Recorded as a claim with whose it is, never
        # merged into a bibliographic field. 258 print works had no completion information from any
        # source; the shop has it and we already take its word for which editions these are.
        _digits = (re.sub(r"[^0-9Xx]", "", str(v.get("isbn") or "")).upper() for v in vols)
        _fin = next((FINISHED_BY_ISBN[_isbn] for _isbn in _digits if _isbn in FINISHED_BY_ISBN),
                    None)
        if _fin:
            w["completed_claim"] = dict(_fin, provenance="claimed")
            # WHICH VOLUME ENDED IT, WITHOUT NEEDING THE SHOP TO NAME IT.
            #
            # This was keyed on the ISBN of the last volume, which meant the shop had to state one
            # there, and コミックシーモア states ISBNs on first volumes. Every claim it could make
            # was about a one-volume work, where the only volume is not a final volume, so the
            # feature fired on nothing. BOOK☆WALKER cannot rescue it either: it sells files and
            # states no ISBN on any of 5,709 volumes read.
            #
            # The shop does not have to name the volume. It says the series is COMPLETE and says
            # how many volumes it has, and our own record says which volume is the Nth. Each side
            # answers what it knows. 114 works are settled this way where 0 were before.
            _stated_vols = _fin.get("volumes") or 0
            if _stated_vols >= 2:
                for _vol in vols:
                    if _vol.get("number_n") == _stated_vols:
                        _vol["final_volume"] = True
                        _vol["final_volume_basis"] = {"source": _fin["source"],
                                                      "provenance": "claimed",
                                                      "volumes": _stated_vols,
                                                      "retrieved": _fin["retrieved"]}
                        break

        # first_publication is the inclusion test and is required (DEFINITIONS §6). What we can
        # attest here is the first 単行本; magazine serialisation is not in the bulk data, so the
        # record says so rather than implying the tankōbon was the original appearance.
        # Take the earliest attested volume date. MADB leads; where it has no date, openBD supplies
        # one, and the record says which source it came from rather than blurring them together.
        # PyYAML turns a full ISO date into datetime.date but leaves YYYY-MM a string, so every
        # date is coerced before comparison or the sort raises on mixed types.
        #
        # EVERY DATE CARRIES ITS BASIS AND NOT ONLY ITS SOURCE. `date_source` names the file the
        # value came out of and `date_basis` names what makes it an answer, and the two are not
        # the same: an enrichment row written by openbd/enrich.py may hold the BIBLIOGRAPHY's date
        # for an ISBN openBD had nothing on, and reading the row's own `published_basis` is what
        # keeps that from being reported as a registration openBD does not have.
        #
        # ONE BINDING RATHER THAN FOUR. `dated` was assembled by three `+=` statements and gained a
        # fourth here, and `adapters/lint/shadowing.py` counts each of those as a rebinding of a
        # name that lives for two thousand lines. Two shipped bugs came from that shape.
        #
        # The last of them is THE BIBLIOGRAPHY REACHED BY TITLE AND A PERSON'S NAME, for a
        # shop's row that states no ISBN. adapters/madb/by_title.py carries what had to agree
        # before that was written, and the record carries the count of what matched, so the join
        # can be withdrawn on better evidence rather than only trusted (DEFINITIONS §5).
        #
        # A VOLUME NOW CARRIES ITS OWN BASIS WHERE THE MERGE ABOVE MOVED ITS DATE, so the first of
        # the four reads the row instead of assuming the bibliography. Assuming it was right while
        # every dated volume came from MADB and would have been silently wrong from the moment one
        # did not, which is the same shape as the row that took every enrichment date for openBD's.
        #
        # A DATE WE DECIDED NOT TO TAKE IS NOT A CANDIDATE FOR THE WORK'S OWN DATE. `published_openbd`
        # was the third of these and it is gone, because it fed the merge's rejects back in through
        # the door the merge had just closed. `min` over strings picks the EARLIEST, so a value the
        # row records as a disagreement won whenever it fell earlier, and 2025-09-08 read off the
        # bibliography shipped as 2025-09 attributed to openBD: a day given back for a month, from
        # the source the merge had ranked second, on a page that named the wrong one of the two.
        # The comment beside `published_openbd` above already said the higher-priority value is kept
        # and the disagreement recorded, and this is the line that made that untrue.
        dated = ([(str(v["published"]), v.get("published_source") or "madb",
                   v.get("published_basis") or "madb-tankobon")
                  for v in vols if v.get("published")]
                 + [(str(o["published"]), "openbd",
                     o.get("published_basis") or "openbd-registration")
                    for o in enrich.values()
                    if o.get("published") and not any(v.get("published") for v in vols
                                                      if v.get("isbn") == o.get("isbn"))]
                 + [(str(o["published"]), "madb", o.get("published_basis") or "madb-tankobon")
                    for o in (by_source.get("madb-title", {}).get("volumes") or [])
                    if o.get("published")])
        if dated:
            date, via, basis = min(dated)
            w["first_publication"] = {
                "date": date,
                "date_source": via,
                "date_basis": basis,
                "venue": base.get("venue") or base.get("imprint", "") or base.get("publisher", ""),
                "venue_type": _dating.venue_type(base.get("date_basis"))
                              or "tankobon-imprint",
                "country": "JP",
                "note": "First known 単行本. Magazine serialisation not attested by current sources.",
            }
        else:
            # No catalogue and no publisher page answered. The shop's own delivery date is taken
            # where the shop states no printing anywhere (DEFINITIONS §6, ruled 2026-08-08), and
            # where there is no date of any kind the absence is STATED rather than left empty and
            # never filled with a platform import stamp. `undated_publication` decides which of the
            # two this is and carries the reasoning for both.
            w["first_publication"] = undated_publication(base)
            _fp_undated = w["first_publication"]
            if _fp_undated.get("date_event") == delivery.EVENT:
                # COUNTED APART FROM THE UNDATED, because it is neither. A row here has a date a
                # reader can act on and the weakest one the database carries, so folding it into
                # either total would lose the distinction the whole ruling turns on. The counting is
                # `delivery.tally`'s, over the finished works-list rows, so the line printed at the
                # end of a build, `run.json` and `status.html` cannot disagree.
                pass
            else:
                undated_works += 1
                _undated_basis = _fp_undated["date_basis"]
                undated_by_basis[_undated_basis] = undated_by_basis.get(_undated_basis, 0) + 1

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

        # THE THIRD BRANCH OF THE INCLUSION TEST. §2 reads "content_tier ≠ incidental OR
        # marketing_label ≠ none OR a comparator lists it", and a licensed retailer's yuri shelf is
        # a comparator (§2, decided 2026-08-04). Such a work carries `marketing_label: none`,
        # because a shop's shelf is never publisher-side labelling (§4), so the two axes cannot
        # admit it and the check below would reject a work the test admits.
        #
        # It is recorded rather than assumed. §2 requires knowing WHICH comparator admitted a work,
        # so a reader can tell whether it is here because a publisher called it yuri or because a
        # shop shelved it there, and the field carries the shelf and the day it was read.
        #
        # AND WHERE THE SHELVING CAN BE READ. The field named the shop and stated no address, so
        # the evidence row built from it carried no citation and the nearest BOOK☆WALKER link on
        # the page was the shop's page for the book, which says nothing about 百合. The shop id is
        # taken from the retailer's own record rather than from `base`, because `base` is the
        # bibliography's record wherever there is one and only the shop knows its own id.
        admitted = base.get("admitted_by")
        if admitted:
            admitted = [cite_shelf(_adm, shelf_cites,
                                   (by_source.get("bookwalker") or {}).get("shop_id"))
                        for _adm in admitted]
            w["admitted_by"] = admitted
            shelf_cited += sum(1 for _adm in admitted if _adm.get("url"))
            shelf_paged += sum(1 for _adm in admitted if _adm.get("page"))

        if not w.get("marketing_label") and not w.get("content_tier") and not admitted:
            errors.append(f"{wid}: fails the inclusion test — neither axis set and no comparator "
                          f"admits it (DEFINITIONS §2)")

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
    #
    # A TAKEDOWN IS NOT THE ONLY WAY A RECORD CAN GO, and §4 did not anticipate the other one. A
    # work leaves this database only by takedown, and that stands. What also happens is that the
    # pipeline WRITES A RECORD IT SHOULD NOT HAVE: the BOOK☆WALKER ingest read 93 titles with the
    # publisher's own imprint still bracketed on the end, so 93 works we already held entered a
    # second time under a name nobody uses. Removing those is not a deletion of a work, it is the
    # retraction of a record that was never valid, and the work stays in the corpus throughout.
    #
    # The guard cannot tell those apart and should not try. It asks for the reason in writing, the
    # same discipline a takedown gets, in data/corrections.yaml.
    out = pathlib.Path(a.out)
    prev = out / "works.json"
    if prev.exists():
        before = len(json.loads(prev.read_text())["works"])
        if len(works) < before:
            allowed = 0
            _cor = pathlib.Path("data/corrections.yaml")
            if _cor.exists():
                _cdoc = yaml.safe_load(_cor.read_text()) or {}
                for _fix in (_cdoc.get("corrections") or []):
                    if str(_fix.get("build_baseline")) == str(before):
                        allowed = int(_fix.get("records") or 0)
                        print(f"correction: {allowed} record(s) retracted, {_fix.get('why')}")
            if before - len(works) > allowed:
                errors.append(
                    f"record count fell {before} -> {len(works)}; a fall needs a takedown record "
                    f"(§4) or an entry in data/corrections.yaml naming the baseline, the count and "
                    f"why. Refusing to write.")

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
    idx = one_row_per_work(idx, works)
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
                # WHERE WITHIN ニコニコ漫画 THE WORK SITS, when the capture read it off the
                # breadcrumb. The block below that renders a channel had no producer since
                # comparator claims stopped being published as releases, so it has not run; the
                # field it wants is `channel`, keyed by name, because platforms.yaml records a
                # channel by name and not by ニコニコ's slug. Only channels platforms.yaml knows
                # resolve, so ニコニコ百合姫 carries none until somebody adds it, and a work in the
                # open section carries none because it is in no channel.
                "channel_src": w.get("channel") or "",
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
    # The third file asks about works whose every date is an import stamp, which is a different
    # question again: those read `unknown` because our dates say when we were told about the work,
    # so the shop is the only party in a position to say whether it ended. All four it answered are
    # marked by the volume tag rather than by 【完結】 in the title, so the title-only reader this
    # module used to be could not have found any of them.
    for _bwf in ("data/coverage/bookwalker-completion.yaml",
                 "data/coverage/bookwalker-completion-slow.yaml",
                 "data/coverage/bookwalker-completion-unknown.yaml",
                 # The second shop. DEFINITIONS §2 admits a licensed retailer as a comparator, and
                 # a shop describing its own stock is the same kind of claim whichever shop makes
                 # it. Read from the 百合・GL genre capture's own row flag.
                 "data/coverage/cmoa-completion.yaml"):
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
        # THE NAME IS RESOLVED HERE because the channel map is built above this point and below
        # where the row is made. platforms.yaml records a channel by NAME, and ニコニコ's own slug
        # joins to nothing without a mapping somebody would have to invent, so the name is what
        # travels.
        if r.get("channel_src"):
            r["channel"] = channels.get(norm_work(r.pop("channel_src")))
        r.pop("channel_src", None)
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
    # WHERE THE ATTRIBUTION CAME FROM, recorded beside the attribution itself.
    #
    # THE WORK PAGE CITES THIS WORK'S FACTS AND DID NOT CITE THIS ONE. `sourced_from` carried
    # volume counts and delivery dates, so a reader could check who catalogued a book's page count
    # and not who says the book is by this person, which is the fact at the top of the page. The
    # project owner's ruling of 2026-08-08 puts it here: the work page says where the ATTRIBUTION
    # came from, and the name's own provenance, the reading and the preferred spelling, belongs to
    # the person and lives on their page.
    #
    # `setdefault` ON BOTH, IN ONE STATEMENT, so the source recorded is the source of the credit
    # that was kept. Written as a second dictionary filled in a second pass, the first file to
    # mention a title would have supplied the citation for a credit a different file supplied.
    author_src = {}
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

        # The document says who read it and when. A work object inside it usually carries its own
        # address, which is the page the byline was on and is better than the file's.
        _doc_src = (_d or {}).get("source") if isinstance(_d, dict) else None
        _doc_src = _doc_src or (_d or {}).get("platform") if isinstance(_d, dict) else _doc_src
        _doc_read = (_d or {}).get("retrieved") if isinstance(_d, dict) else None

        def _seen(o):
            if isinstance(o, dict):
                t = next((o[k] for k in ("work_title", "title", "name")
                          if isinstance(o.get(k), str) and o[k].strip()), None)
                a = next((_author_str(o[k]) for k in
                          ("author", "authors", "author_on_page", "author_name")
                          if _author_str(o.get(k))), None)
                if t and a:
                    k = norm_work(t)
                    if k not in author_of:
                        author_of[k] = a
                        # A SOURCE WITH NO NAME IS NOT CITED. Some captures state no `source` at
                        # all, and inventing one out of the file path would put our own directory
                        # layout in front of a reader as though it were a publisher.
                        if _doc_src:
                            author_src[k] = {"source": str(_doc_src),
                                             **({"read": str(_doc_read)} if _doc_read else {}),
                                             **({"url": o["url"]} if isinstance(o.get("url"), str)
                                                and o["url"].startswith("http") else {})}
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
                    k = norm_work(m.group(1))
                    if k not in author_of:
                        author_of[k] = m.group(2).strip()
                        if _doc_src:
                            author_src[k] = {"source": str(_doc_src),
                                             **({"read": str(_doc_read)} if _doc_read else {})}
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
            title = work_alias((w.get("work_title") or "").strip())
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
            #
            # PARTIAL IS A PROPERTY OF THE ROUTE, NOT OF THE PLATFORM, and マガポケ is why that
            # distinction now has to be made. Three routes read its page and all three saw the
            # free window; the feed it publishes per series carries the whole run, and its item
            # count agrees with the series page's own episode_id_list. Naming the platform here
            # would have gone on calling 私の百合はお仕事です! ten chapters long while a file on
            # disk held all 147. The three page-reading files stay named, so nothing they claim
            # alone is promoted, and `bucket["partial"]` already requires EVERY source for a row
            # to be partial before the count is hedged.
            #
            # A ROUTE CAN ALSO BE PARTIAL FOR ONE WORK AND NOT THE NEXT, and where the page says
            # so the record carries it. ニコニコ漫画 renders the episodes a signed-out reader may
            # open: for オレは男装女子じゃない！ that is all 37, and for 運命のヤマダダダダダダダ
            # ダダダ it is five out of a run whose own position numbers reach 17. Naming the
            # platform here would report the first as a fraction of something longer, which is the
            # opposite error and no better. `nicovideo/works.py` compares the two numbers.
            partial = bool(w.get("partial")) or _d.get("source") in ("sitemap",) or _d.get(
                "platform") in (
                "pixivcomic", "ganganonline", "mangaone", "backfill", "remaining",
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
            oneshot_why = None
            if w.get("is_oneshot"):
                oneshot_why = "platform-confirmed"
            elif _chs and all(ONESHOT_RE.search(c.get("title") or "") for c in _chs):
                oneshot_why = "every-chapter-marked"
            elif ONESHOT_RE.search(title or "") and len(_chs) == 1 and not partial:
                # THE MARKER IN THE WORK TITLE, which the feed path has always read and this one
                # never did (§3). チャンピオンクロス and ヤンチャンWeb write it there: the work is
                # `ガラスノキック/読み切り` and its only instalment is `ガラスノキック`, so the
                # chapter test above cannot see it and seven works were filed as serialisations we
                # hold one chapter of. Gated on holding exactly one full instalment, because a
                # pilot that gets serialised keeps the title it was published under, and the
                # marker must stop deciding the moment a second chapter lands.
                oneshot_why = "work-title-marked"
            oneshot_src = bool(oneshot_why)
            bucket_key = (norm_work(title), plat)
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
            bucket = series.setdefault(bucket_key, {
                "work": title, "platform": plat, "url": None, "feed_url": None,
                "author": "", "chapters": {}, "upcoming": 0,
                "partial": True, "oneshot_src": False, "oneshot_why": None,
                "completed_src": None,
                "running_src": None, "_srcs": set(),
                "retrieved": None, "label_rec": None,
            })
            bucket["_srcs"].add(_d.get("platform") or _d.get("source") or "")
            # WHEN THIS PLATFORM WAS LAST READ. The newest answer across the files describing the
            # row, because a chapter list and a confirmation record are two readings of one site
            # and the reader wants the later one.
            _readon = str(_d.get("retrieved") or "")[:10]
            if _readon > (bucket["retrieved"] or ""):
                bucket["retrieved"] = _readon
            # THE PLATFORM'S OWN YURI TAG, kept as evidence rather than collapsed into the label.
            # カドコミ is the only platform stating one today, on 350 works. The record is carried
            # whole so credence.py can quote the tag; deciding here what the term is would put the
            # same judgement in two places.
            if (w.get("marketing_label_basis") or {}).get("source") and not bucket["label_rec"]:
                bucket["label_rec"] = {"marketing_label": w.get("marketing_label"),
                                       "marketing_label_basis": w["marketing_label_basis"],
                                       "tags": w.get("tags")}
            bucket["oneshot_src"] = bucket["oneshot_src"] or oneshot_src
            # WHICH ROUTE SAID SO, kept beside the boolean so the row can publish the reason.
            # The strongest of the routes any source for this row reached, because a work whose
            # platform states 読み切り should not show a reader our guess about its title.
            bucket["oneshot_why"] = stronger(bucket.get("oneshot_why"), oneshot_why)
            bucket["oneshot_plat"] = bucket.get("oneshot_plat") or (plat if oneshot_why else None)
            # The platform's own statement that the serialisation is over, where it makes one.
            # カドコミ's serializationStatus takes three values across the works we hold — unknown
            # 217, ongoing 92, finished 91 — so `finished` is a real assertion and not a default.
            # カドコミ answers in English and comici in Japanese, in a field of the same name.
            # comici has no value meaning "we do not know": a page carrying the field has answered,
            # which is why 連載中 is worth recording as well and not only its opposite.
            #
            # THE NAME, NOT A SENTENCE. Both fields used to hold prose reading "the platform marks
            # the serialisation finished", which is a source's claim welded to our wording of it and
            # said nothing about WHICH platform on a work serialising in three places. What they
            # carry now is the platform's own name, so the sentence can be composed where it is
            # needed and `state_claim` below can be a row like every other fact on the page.
            platform_status = str(w.get("status") or "")
            _ended = platform_status.lower() == "finished" or platform_status == "完結"
            _says = ("completed" if _ended
                     else "running" if platform_status in ("ongoing", "連載中") else None)
            if _says:
                bucket["completed_src" if _ended else "running_src"] = plat
                # WHAT IT SAID, IN ITS OWN WORD. `says` is our reading of the field and `term` is
                # the value the platform stated, so a reader can see that カドコミ answers
                # `finished` in English where comici answers 完結, which is two sources agreeing
                # rather than one fact with two spellings.
                #
                # A completed claim wins a disagreement, which is the precedence the branch far
                # below already applies to `completed_src`. Without it a row would say one thing or
                # the other according to which of two files describing it was read last.
                if _ended or not bucket.get("state_claim"):
                    bucket["state_claim"] = {"says": _says, "term": platform_status}
            elif platform_status == "読み切り":
                bucket["oneshot_src"] = True
                bucket["oneshot_why"] = stronger(bucket.get("oneshot_why"), "platform-status")
                bucket["oneshot_plat"] = plat
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
            _can_testify = can_testify(chs)
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
                        "partial": False, "oneshot_src": True,
                        "oneshot_why": "collection-instalment", "oneshot_plat": plat,
                        "_srcs": {"collection"},
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
                #
                # BUT SILENCE IS NOT TESTIMONY. `_stamped` is computed per file, so a file holding
                # one chapter of a work cannot see a run and never reports one, and the old test
                # read that inability as an observation. sitemap-magapoke.yaml holds a single
                # chapter of ハロー、メランコリック！ at 2021-11-11, and that one row unmade the stamp
                # both files holding all 40 chapters agreed on, so the work read `dormant` off the
                # day 講談社 loaded it onto the platform and showed 【track1】 as its newest episode.
                #
                # A source may say a date was observed only where it holds enough of the work to
                # have noticed an import: more than one distinct date for that work in that file.
                # One date across every chapter a file holds is the signature itself, not evidence
                # against it.
                if _can_testify and (w.get("work_title"),
                                     str(c.get("updated") or "")[:10]) not in _stamped:
                    slot["date_observed"] = True

    # Collapse each bucket's merged chapters into the row the interface reads.
    for row in series.values():
        chs = sorted(row.pop("chapters").values(), key=lambda c: str(c.get("updated") or ""))
        row["chapters_list"] = chs
        row["chapters"] = collapsed_length(chs)
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
        row["free"] = sum(1 for c in chs
                          if "free" in (c.get("access_modes") or []) and readable_now(c))
        row["free_timed"] = sum(1 for c in chs
                                if "free-timed" in (c.get("access_modes") or []) and readable_now(c))
        row["priced"] = sum(1 for c in chs
                            if "purchase" in (c.get("access_modes") or []) or not readable_now(c))
        if not row["author"]:
            row["author"] = next((c["author"] for c in reversed(chs) if c.get("author")), "")
        # AND FROM ANY OTHER RECORD OF THE SAME WORK, which is where a byline read off the work's
        # own page arrives. A chapter list has no room for a fact about the work, so the six
        # platforms whose adapters only ever read chapters state their author in a record with no
        # chapters in it at all, and a row assembled purely out of chapters never meets it. This is
        # the same `author_of` the feed rows are filled from a few hundred lines above, consulted
        # rather than re-derived.
        if not row["author"]:
            row["author"] = author_of.get(norm_work(row["work"]), "")
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
        _rowkey = (norm_work(row["work"]), row["platform"])
        # A work with ONE chapter whose chapter title is the work's own title is a 読切. Platforms
        # name a one-shot's only episode after the work — 神様やめらんない / 神様やめらんない — and the
        # marker-based test misses every one that does not also print 読切. Those were being filed
        # `dormant`, which reads as abandoned when the thing is simply finished.
        _self_named = (row["chapters"] == 1 and not row["partial"]
                       and norm_work(row.get("latest_ep") or "") == norm_work(row["work"]))
        _rev_one = reviewed.get(norm_work(row.get("work") or ""))
        _rev_one = _rev_one if (_rev_one or {}).get("verdict") == "oneshot" else None
        _feed_said = (_rowkey in _oneshot
                      or (row["chapters"] == 1 and not row["partial"]
                          and norm_work(row["work"]) in _oneshot_any))
        _os_route = stronger(row.pop("oneshot_why", None),
                             "review" if _rev_one else "feed" if _feed_said
                             else "self-named" if _self_named else None)
        row["oneshot"] = bool(row.pop("oneshot_src", False) or _os_route)
        # WHY, IN BOTH LANGUAGES, on the row that publishes an unhedged length. A reviewed verdict
        # brings its own sentences and outranks every rule, because somebody read a page and wrote
        # down which one; the rules describe themselves from ONESHOT_WHY.
        if row["oneshot"]:
            if _rev_one and _os_route == "review":
                row["oneshot_basis"] = _rev_one.get("basis_en") or _rev_one.get("basis")
                row["oneshot_basis_ja"] = _rev_one.get("basis")
                row["oneshot_inferred"] = False
                row["oneshot_source_url"] = _rev_one.get("source_url")
            else:
                _os_en, _os_ja, _os_inferred = oneshot_basis(
                    _os_route, row.pop("oneshot_plat", None))
                row["oneshot_basis"], row["oneshot_basis_ja"] = _os_en, _os_ja
                row["oneshot_inferred"] = _os_inferred
        row.pop("oneshot_plat", None)
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
        _behind_rev = reviewed.get(norm_work(row.get("work") or "")) if row.get("_capture_behind") \
            else None
        if row.pop("_capture_behind", False) and not (_final or _completed) \
                and not (_behind_rev and _behind_rev.get("verdict") in _comp.ENDED):
            # The platform lists chapters past the newest we hold, so our newest is not the
            # series' newest and its age measures our capture rather than the work.
            #
            # A HAND REVIEW OUTRANKS THIS, which is why the verdict is consulted before the branch
            # rather than in the `else` below where the other review checks sit. `unknown` here is
            # a statement about our capture, and a cited page saying the series finished is a
            # statement about the work; the two are not in competition. 惑星クローゼット is the
            # case: pixivコミック lists 37 chapters against the 3 we hold, so the row read `unknown`
            # while BOOK☆WALKER tagged all four volumes 完結. Reaching the review only through the
            # `else` made a short capture able to suppress the better evidence.
            row["state"] = "unknown"
            row["state_basis"] = (
                f"{_sl['n']} chapters are listed on the platform and we hold {row['chapters']}, "
                f"none of them the newest, so nothing here says when this last updated")
        elif not row["latest"]:
            row["state"] = "unknown"
        elif row["oneshot"]:
            row["state"] = "oneshot"
            # THE REASON TRAVELS WITH THE STATE, like every other state on this row. The interface
            # already reads `state_basis` for its Basis line, so putting the sentence here needs
            # nothing of the interface and gives 読切 the same accountability 完結 has had.
            row["state_basis"] = row.get("oneshot_basis")
            row["state_basis_ja"] = row.get("oneshot_basis_ja")
        elif _final or _completed:
            row["state"] = "completed"
            # Quoting what was actually found. The pattern accepts 最終話 and a bracketed 完
            # alike, and a basis naming the wrong one is a citation to something the page does
            # not say.
            #
            # THE PLATFORM IS NAMED. `_completed` is its name now, so the sentence says which site
            # said it. It used to read "the platform marks the serialisation finished", which on a
            # work running in three places left the reader to guess which of the three.
            row["completed_basis"] = (f"the newest chapter is titled {_fm_shown.group(0)}"
                                      if _final
                                      else f"{_completed} marks the serialisation finished")
            # THE SAME EVIDENCE IN THE READER'S LANGUAGE. The site is bilingual and every one of
            # these sentences was English, so a Japanese reader was shown prose they could not use
            # in the one place the interface explains itself. Written beside the English at the
            # moment the finding is made, rather than translated later from the sentence.
            #
            # It used to be read off `bucket`, which is the ingest loop's variable and had gone out
            # of use hundreds of lines earlier: every completed row was given the LAST bucket's
            # Japanese, and the fault was invisible only because the sentence was a constant.
            row["completed_basis_ja"] = (f"最新話の題が{_fm_shown.group(0)}"
                                         if _final
                                         else f"{_completed}が連載終了と表示している")
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
                # A GAP OF ZERO DAYS IS NOT A GAP. The newest chapter arrived today, and saying
                # "no chapter for 0 days" reads as a fault in the database where the fact is the
                # opposite. 6 rows said it, the most recently updated works in the corpus.
                row["state_basis"] = (
                    "a chapter arrived today, and nothing states it has ended" if age == 0 else
                    f"no chapter for {age} day{'' if age == 1 else 's'}, "
                    f"and nothing states it has ended")
                row["state_basis_ja"] = ("本日新しい話があり、終了したとする情報もない" if age == 0
                                         else f"{age}日間新しい話がなく、終了したとする情報もない")
                # A PLATFORM SAYING IT IS RUNNING IS NOT SILENCE. It does not make a quiet work
                # active, because a serialisation can be open and on hiatus at once, and the
                # silence is still what we observed. What it does is say the silence is ours: the
                # publisher has not ended this, so the reader is owed the distinction between a
                # work nobody has closed and a work nobody has touched. カドコミ marks six of its
                # ten dormant works ongoing, and it is also what keeps an aggregator's 完結 tag
                # from closing a work the platform itself still calls running.
                #
                # THE TWO HALVES ARE NOW SEPARABLE. This sentence welds a source's claim to our own
                # coverage, and the page could do nothing with either: `age_days` is on the row and
                # the platform's claim is on `state_claims`, both structured, both rendered as rows.
                # The prose stays because it is what the badge tooltip reads, and because the JOIN
                # is the point: that the silence is ours rather than the work's is a statement
                # neither half makes alone.
                _running_on = row.pop("running_src", None)
                if _running_on:
                    row["state_basis"] = (
                        f"a chapter arrived today, and {_running_on} marks the serialisation as "
                        "running" if age == 0 else
                        f"no chapter for {age} day{'' if age == 1 else 's'} in what we hold, but "
                        f"{_running_on} still marks the serialisation as running")
                    row["state_basis_ja"] = (
                        f"本日新しい話があり、{_running_on}は連載中と表示している" if age == 0 else
                        f"{age}日間新しい話がないが、{_running_on}は連載中と表示している")
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
                if _rev and _rev.get("verdict") in _comp.ENDED:
                    row["state"] = "completed"
                    # THE READER'S LANGUAGE FIRST WHERE THE REVIEW WROTE ONE. Every sentence in
                    # this register is Japanese, so this field has been handing Japanese to an
                    # English page since it was written. `basis_en` is required of a oneshot
                    # verdict and welcome on any, so it is preferred here and the Japanese stays
                    # available beside it.
                    _rb = _rev.get("basis_en") or _rev["basis"]
                    row["completed_basis"] = (
                        f"{_rb} ({_rev.get('source') or _rev.get('source_kind')}"
                        + (f", {_rev['source_url']}" if _rev.get("source_url") else "") + ")")
                    if _rev.get("basis_en"):
                        row["completed_basis_ja"] = _rev["basis"]
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
    # A work with a print record HAS been assessed: it is in the print corpus under a publisher's
    # imprint, with a marketing_label and a basis. Leaving it out of scope made in-scope-ness
    # depend on having a release inside the feed window, which a work whose whole run carries one
    # import stamp can never have. 月が綺麗ですね, 徒然日和, 乙女ケーキ and マーメイドライン all left
    # the database that way: 一迅プラス stamped their runs 2026-06-05 and 2025-08-08, no release
    # fell in the window, and four works we hold both in print and on the web silently vanished.
    _cands |= {norm_work(w["title"]["ja"]) for w in works if w.get("title", {}).get("ja")}
    # An instalment is in scope because the collection it appeared in was assessed, not because a
    # discovery list names it — 貝合わせ appears on no candidate list and is nonetheless a work we
    # hold, attested, with its own author.
    _cands |= {norm_work(v["work"]) for v in series.values() if v.get("collection")}
    # AN ADDRESS THE REGISTRY ALREADY ANSWERS FOR IS IN SCOPE, whatever the platform calls the
    # work. Every rule above matches a TITLE, and a platform's title is not the bibliography's:
    # ニコニコ carries アイドル総選挙4位だった私が魔王を倒すんですか？ with （Lilie comics） on the
    # end and カドコミ carries 専門学校JK as 専門学校JK Ctrl+Z. 26 serialisations joined to printed
    # records we hold were dropped here for that alone, which is the scope test contradicting a
    # join the registry had already made on a person's name.
    _idfile = pathlib.Path("data/identity/works.yaml")
    _reg_doc = yaml.safe_load(_idfile.read_text()) if _idfile.exists() else None
    _reg_index = identity.index((_reg_doc or {}).get("works") or [])
    _known_web = {a for a in _reg_index if a.startswith("web:")}
    _before = len(series)
    series = {k: v for k, v in series.items()
              if k[0] in _cands or identity.web_anchor(v.get("url")) in _known_web}
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

    # ROWS SHARING AN IDENTIFIER ARE ONE WORK, WHATEVER EACH PLATFORM CALLS IT. Grouping by title
    # cannot see that: ニコニコ漫画 carries 不器用ビンボーダンス as three series, one per volume, and
    # its titles are 不器用ビンボーダンス, ２ and ３. All three are joined to one printed record, so
    # all three answer to one identifier, and grouping by title alone gave the works list one work
    # three times under one id. `one row per identifier` is the invariant that catches it.
    #
    # This UNIONS title groups and never splits one. A row whose address the registry does not yet
    # know keeps its title key, so a platform read for the first time still joins the work it
    # belongs to, exactly as before. The first title key seen for an identifier is the one the
    # others fold into.
    _key_of_id = {}
    for _grow in series.values():
        _gkey = norm_work(_grow["work"])
        _gkey = _gkey if _gkey not in distinct else f"{_gkey}|{_grow['platform']}"
        _gid = _reg_index.get(identity.web_anchor(_grow.get("url")))
        _grow["_group"] = _key_of_id.setdefault(_gid, _gkey) if _gid else _gkey

    # Read once for the whole population; 3,000 rows would otherwise re-parse an 843-entry capture.
    _work_addresses = work_level_addresses(
        yaml.safe_load(pathlib.Path(_wl).read_text()) or {}
        for _wl in sorted(glob.glob(WORK_ADDRESS_CAPTURES)))

    works_out, by_title = [], defaultdict(list)
    for row in series.values():
        row["format"] = editions.get((norm_work(row["work"]), row["platform"]), "standard")
        by_title[row.pop("_group")].append(row)

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
                _state_basis = (f"no chapter for {_age} day{'' if _age == 1 else 's'} on any "
                                f"platform we watch; the newest we hold is {_merged_latest}")
        works_out.append({
            "work": best["work"],
            "author": next((r["author"] for r in rows if r["author"]), ""),
            # The BEST-KNOWN length, not a sum: every source is describing the same story, and
            # adding them would report 135 chapters for a 121-chapter work. See the function.
            "chapters": demonstrable_length(
                rows,
                max((r["chapters_stated"] for r in rows if r.get("chapters_stated")), default=0),
                best["latest_ep"]),
            # What the platform says the series is long, where we hold less. Published so the
            # count can read as "what we have" rather than as the length of the work. Taken across
            # every row for the same reason the length is: whichever source states it, states it.
            **({"chapters_stated": max(r["chapters_stated"] for r in rows
                                       if r.get("chapters_stated"))}
               if any(r.get("chapters_stated") for r in rows) else {}),
            "partial": all(r["partial"] for r in rows),
            "latest": max((r["latest"] for r in _dr if r["latest"]), default=None),
            "latest_ep": best["latest_ep"],
            "first": min((r["first"] for r in _dr if r["first"]), default=None),
            "state": _state, "oneshot": best["oneshot"],
            # WHETHER THE ONE-SHOT CALL IS OURS. The sentence itself travels as `state_basis` below,
            # which is the field the interface already reads; this is the flag beside it, so a
            # reading of a shape can be marked as one wherever a source's statement is not.
            **({"oneshot_inferred": True} if best.get("oneshot_inferred") else {}),
            # Why we say it ended, carried up with the state. A state without its basis is the
            # thing this project keeps having to unpick.
            # THE BASIS HAS TO DESCRIBE THE STATE BEING PUBLISHED. `state` comes from `best`, and
            # these took the first basis any row carried, so a work could publish one platform's
            # state beside another platform's reason for it. はなにあらし read `active` with its
            # last chapter a month old, above a line saying no chapter had appeared for 2946 days:
            # サンデーうぇぶり has 169 chapters ending last month, pixivコミック has 3 ending in
            # 2018, and the row took the state from one and the sentence from the other.
            "completed_basis": _basis_of(best, rows, "completed_basis"),
            # The Japanese travels with the English, from the same row, by the same rule.
            "completed_basis_ja": _basis_of(best, rows, "completed_basis_ja"),
            # Same reasoning for a paused series: the state travels with what it rests on, and
            # the skipped slots themselves are kept as dated evidence rather than summarised away.
            # A recomputed state brings its own reason. Taking the row's would publish one
            # platform's explanation for a state that platform did not decide.
            "state_basis": (_state_basis if _state != best["state"]
                            else _basis_of(best, rows, "state_basis")),
            "state_basis_ja": (None if _state != best["state"]
                               else _basis_of(best, rows, "state_basis_ja")),
            "skipped": sorted(
                {(x.get("date"), x.get("title")) for r in rows for x in (r.get("skipped") or [])},
                reverse=True),
            "collection": best.get("collection"),
            "url": best["url"],
            # THE ADDRESS THAT DOES NOT MOVE. `url` above is the newest chapter's, so anchoring a
            # work on it mints a second identifier the next time the work publishes. This is the
            # work's own address on the same platform, and it belongs beside `url` rather than
            # instead of it: a reader following a row wants the chapter it is telling them about.
            "series_url": series_address(best, _work_addresses),
            "free": best["free"], "free_timed": best["free_timed"], "priced": best["priced"],
            "sources": [{"platform": r["platform"], "url": r["url"], "chapters": r["chapters"],
                         "free": r["free"], "free_timed": r["free_timed"], "priced": r["priced"],
                         "latest": r["latest"], "partial": r["partial"], "format": r["format"],
                         "retrieved": r.get("retrieved")}
                        for r in rows],
            # WHY THIS WORK IS FILED AS YURI, as far as the platforms go. One row per platform
            # that applied its own tag; the print half is joined on further down, once the
            # identifier has attached each row's book records. Ordering happens there, once.
            "evidence": [_ev for _ev in (credence.label_row(r["label_rec"], platform=r["platform"])
                                         for r in rows if r.get("label_rec")) if _ev],
            # WHETHER THE PLATFORM SAYS IT IS STILL RUNNING, as a row rather than as prose. Every
            # row here, not only the one the state was taken from: two platforms carrying one work
            # can disagree, and a reader owed the state's basis is owed the disagreement with it.
            "state_claims": state_claim_rows(rows),
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
    # THE POPULATION HAS TO BE COMPLETE BEFORE ANYTHING IS ATTACHED TO IT. Identity and the
    # print-only rows used to run AFTER the naming pass below, so every print work reached
    # series.json with work_en absent however many names the store held: 楽園の条件 had a
    # licensed title curated, applied and shipped in names.json, and its row still rendered
    # Japanese. Two producers of one fact again, and the second one ran too late to see the
    # first. Nothing here reads a name, so it costs nothing to do it first.

    # A work's identifier, so the interface can address it. Minted and stored by
    # adapters/identity.py, which is imported rather than reimplemented: the anchor rule is one
    # fact and a second copy of it here would drift the moment either side changed. A row with no
    # id is a work registered since the last identity run, which is a state the interface has to
    # tolerate rather than a reason to fail the build.
    _idreg = pathlib.Path("data/identity/works.yaml")
    if _idreg.exists():
        _iddoc = yaml.safe_load(_idreg.read_text()) or {}
        _byanchor = identity.index(_iddoc.get("works") or [])
        _shared = Counter(r.get("url") for r in series_rows if r.get("url"))
        # The print half of a joined work, carried onto the row so the interface can show one work
        # rather than a web row and a print row a reader has to notice are the same thing. The
        # registry already holds the join and its evidence; this only reads it.
        _print_by_id = {}
        for _e in _iddoc.get("works") or []:
            _mad = [x[5:] for x in (_e.get("anchors") or []) if x.startswith("madb:")]
            if _mad and not _e.get("merged_into"):
                _print_by_id[_e["id"]] = _mad
        _pw = {w["work_id"]: w for w in works if w.get("work_id")}
        _named = _joined = 0
        for _srow in series_rows:
            _anchor = identity.web_anchor(_srow.get("url"), _srow.get("work"),
                                          _shared[_srow.get("url")] > 1)
            _found_id = _byanchor.get(_anchor)
            if _found_id:
                _srow["id"] = _found_id
                _named += 1
                _eds = [_pw[m] for m in _print_by_id.get(_found_id, []) if m in _pw]
                if _eds:
                    _srow["print"] = [_print_block(_e2) for _e2 in _eds]
                    _joined += 1
        print(f"work identifiers: {_named} of {len(series_rows)} rows carry one; "
              f"{_joined} also carry their print edition")

        # THE PRINT-ONLY POPULATION JOINS THE WORKS LIST. It used to live in a tab of its own,
        # which is how one database came to hold two populations a reader had to notice were the
        # same kind of thing. A work that exists only in print is still a work: it has no chapters
        # and no serialisation state, and the row says so rather than inventing either.
        _seen_print = {p2["work_id"] for r2 in series_rows for p2 in (r2.get("print") or [])}
        # TWO PRINT RECORDS THAT ARE ONE WORK GET ONE ROW. `--merge` retires an identifier and both
        # records then resolve to the surviving id, but each was still appended here on its own
        # work_id, so the list held the work twice under one id: 13 pairs, every one of them a
        # merge. The registry decides identity and this reads it, so a record whose id already has
        # a row joins that row's editions instead of starting a second one. Which title the reader
        # sees is the first record's, and `works` is sorted by work_id, so a bare shop title is
        # preferred over the bibliography's ISBD form (`X = parallel title`), which is the form
        # nobody writes.
        # Seeded with the rows that already carry an id, so a print record whose identity belongs
        # to a web row lands on that row. `_print_by_id` above cannot reach this case: it reads
        # each live entry's own anchors, and a retired entry's anchors stay with the retired entry.
        _row_by_id = {_r3["id"]: _r3 for _r3 in series_rows if _r3.get("id")}
        _added = _folded = 0
        for _pw2 in works:
            if _pw2.get("work_id") in _seen_print:
                continue
            _pid = _byanchor.get("madb:" + str(_pw2.get("work_id")))
            _fp2 = _pw2.get("first_publication") or {}
            if _pid and _pid in _row_by_id:
                _row_by_id[_pid].setdefault("print", []).append(_print_block(_pw2))
                _folded += 1
                continue
            # MADB writes a credit as cataloguing notation: `[著]秋山はる`, `[作画]A / [原作]B`,
            # and `[[著]]椿木とりか` with the delimiter doubled. The work page was showing the
            # bracket to readers on all 470 print rows. One reader of that notation, in
            # openbd_reading, because a second copy here would drift from it.
            #
            # WHAT THE BRACKET SAID IS KEPT BESIDE THE NAME IT BELONGED TO. The notation is the
            # only place a print row states a job, and taking it off was the end of it, so a page
            # built over these rows could say who is on a book and never what they did.
            _cparts = [openbd_reading.credit_parts(part)
                       for part in re.split(r"\s*/\s*", _pw2.get("creator") or "")]
            _cparts = [(x, r) for x, r in _cparts if x]
            series_rows.append({
                # ALIASED HERE TOO, and it was reached only from the web path. A curated alias
                # says which of two spellings names the work, and a print-only row could not ask:
                # フィダンツァートのためいき : 完全版 is 一迅社's 2018 reissue of a 2010 book the house
                # lists under the plain name, and the ISBD colon marked the edition.
                "work": work_alias(((_pw2.get("title") or {}).get("ja") or "").strip()),
                "author": " / ".join(x for x, _job in _cparts),
                **({"credits": [{"name": x, **({"role": j} if j else {})} for x, j in _cparts]}
                   if any(j for _x, j in _cparts) else {}),
                "chapters": 0, "partial": False, "oneshot": False,
                "latest": None, "latest_ep": "", "first": _fp2.get("date"),
                # WHICH EVENT THE DATE IS OF, carried because `first` is not one fact across the
                # corpus: a chapter on a serialisation, a printing on a book, and on 1,297 rows the
                # day a shop began delivering a file. The works list labels the date and cannot
                # label it correctly without being told which it has.
                **({"first_event": _fp2["date_event"]} if _fp2.get("date_event") else {}),
                **({"first_followup": _fp2["date_followup"]} if _fp2.get("date_followup") else {}),
                "state": "print", "state_basis": None, "completed_basis": None,
                "free": 0, "free_timed": 0, "priced": 0,
                # A work that exists only in print serialises nowhere, so it has no address of
                # either kind and no platform to make a claim about a serialisation it lacks.
                "url": None, "series_url": None, "sources": [], "skipped": [], "collection": None,
                "state_claims": [],
                "id": _pid,
                "completed_claim": _pw2.get("completed_claim"),
                "print": [_print_block(_pw2)],
            })
            if _pid:
                _row_by_id[_pid] = series_rows[-1]
            _added += 1
        print(f"print-only works added to the works list: {_added}"
              + (f"; {_folded} editions folded into a row already held" if _folded else ""))

        # A WORK IS AS OLD AS THE OLDEST THING WE HOLD ABOUT IT. The row's date came from the
        # platform's own chapters, which is the day the platform posted them and not the day the
        # work first appeared. Where a platform re-serialises a finished title, the two are years
        # apart: ワインガールズ read 2026-04-19 against volumes that began in 2017-12, and 140 rows
        # across 12 platforms had a collected edition predating their own first date.
        #
        # `importdates` does not reach this. It looks for a bulk stamp, many works landing on one
        # day, and a slow re-run of one title leaves no such signature. The evidence here is the
        # print run instead, and it only became readable once the book runs were attached.
        #
        # THE EARLIEST VOLUME IS STILL LATE. It is the collected edition of a serialisation that
        # ran before it, so this moves the date toward the truth without claiming to reach it. It
        # is taken only when it is EARLIER than what the row holds, so an ordinary work, serialised
        # and then collected, keeps its serialisation date and is untouched.
        # THE OPERATOR'S ANSWER TO A COMPARATOR ADMISSION, carried to the row so the interface can
        # keep a doubtful entry out of a default listing without losing it. See rebuttals().
        # A PRINTING BEATS A DELIVERY ON THE SAME WORK, and the rule had nowhere to run once two
        # records became one. `delivery.promote` refuses a delivery date where the record states a
        # printing, which is right per record; merging two records puts a delivery-dated block
        # beside a printed one, and the work then carried the shop's date while its own book had a
        # colophon. SIS reads 2012-06 in print and was delivered in 2016; 私たちの恋が花開くとき was
        # delivered 2026-01-05 and printed 2026-01-16.
        #
        # The delivery date is NOT discarded. It stays on the block it belongs to, because it is a
        # true statement about that edition; what it stops doing is standing for the work.
        for _srow in series_rows:
            _blocks = _srow.get("print") or []
            _printed = [b.get("first") for b in _blocks if b.get("first")]
            if not _printed:
                continue
            for _b in _blocks:
                _b.pop("delivered_from", None)
            if _srow.get("first_event") == "shop-delivery":
                _srow["first"] = min(_printed)
                _srow.pop("first_event", None)
                _srow.pop("first_followup", None)

        _rebut = rebuttals()
        _marked = 0
        for _vrow in series_rows:
            _how = _rebut.get(_vrow.get("id"))
            if _how:
                _vrow["visibility"] = _how
                _marked += 1
        if _marked:
            print(f"works held out of the default listing: {_marked}")

        # THE ROW'S OWN STRING IS WHAT THE PAGE PRINTS, and it kept the raw while the composer read
        # a cleaned copy, so `&nbsp;フォローする` and `大島永遠&amp;大島智` reached the page with the
        # escape intact. Rebuilt from the parts the splitter returns, which unescapes and drops a
        # control's own label. Run here because the print-only rows are appended above this point,
        # and an earlier pass missed every one of them.
        #
        # A FIELD THAT WAS ALL FURNITURE BECOMES EMPTY, not left as it was. `works crediting nobody`
        # counts an empty credit and counts nothing at all for a button, so leaving the button in
        # hides the gap it should be reporting.
        # AND THE JOB EACH PART WAS DOING SURVIVES THE REBUILD, which it did not. The role notation
        # is what the rebuild takes off, so `原作／宮澤伊織　作画／水野英多` reached the works list
        # as `宮澤伊織 / 水野英多` and nothing downstream could say who wrote and who drew: 3,076 of
        # 3,077 rows named nobody's job, and the credit registry, which reads this field, could
        # hang a role on 14 of its 4,350 edges.
        #
        # THE STRING A READER SEES IS UNCHANGED. The roles travel beside it as `credits`, one entry
        # per part in the order they were written, because the display string has three consumers
        # that all expect the parts to add up to it: the ruby splicer, the composed romanisation
        # and the phrase map. Putting the notation back into the field would have been a fourth
        # opinion about what that string is, and the bracket it arrives in was shown to readers on
        # 470 print rows once already.
        _cleaned = _roled = 0
        for _crow in series_rows:
            _raw = _crow.get("author") or ""
            if not _raw:
                continue
            _parts_roled, _join = _credits.split_credits_roled(_raw)
            _rebuilt = _join.join(n for n, _job in _parts_roled)
            if _rebuilt != _raw:
                _crow["author"] = _rebuilt
                _cleaned += 1
            if any(_job for _n, _job in _parts_roled):
                _crow["credits"] = [{"name": _n, **({"role": _job} if _job else {})}
                                    for _n, _job in _parts_roled]
        if _cleaned:
            print(f"credit fields rebuilt from their parts: {_cleaned}")
        # Counted after the loop rather than inside it, because the print rows carry theirs from
        # the bracket notation MADB writes and never pass through the branch above.
        _roled = sum(1 for _crow in series_rows
                     if any(c.get("role") for c in (_crow.get("credits") or [])))
        print(f"works whose credit field states a job: {_roled} of {len(series_rows)}")

        _redated = 0
        for _drow in series_rows:
            _pf = [p3.get("first") for p3 in (_drow.get("print") or []) if p3.get("first")]
            if not _pf:
                continue
            _earliest = min(_pf)
            if _drow.get("first") and _earliest[:7] < _drow["first"][:7]:
                _drow["first"] = _earliest
                _redated += 1
        if _redated:
            print(f"first-publication dates moved back to a collected edition: {_redated}")

        # THE LAST THING THAT HAPPENED, WHICHEVER KIND IT WAS, AS A SEPARATE FIELD FROM THE ONE
        # THAT DECIDES STATE. A reader scanning the list wants to know when the work last did
        # anything; `latest` answers only when the serialisation last updated, so a work whose
        # volume shipped last month reads as a year stale.
        #
        # `latest` IS NOT TOUCHED, and that is the whole point. A print release says nothing about
        # whether a web series is alive: volumes trail the serialisation by design, so a volume of
        # a run that stopped in 2022 still ships in 2024. State is a claim about the serialisation
        # and it keeps being decided by the serialisation's own date, which is also what
        # `state agrees with its own date` compares. Overwriting `latest` here would have made
        # every one of these rows contradict its own state label.
        #
        # The kind travels with the date because the reader cannot otherwise tell which question
        # the date answered, and a volume date shown as though it were a chapter date is the same
        # category error in a different place.
        _anydate = 0
        for _evrow in series_rows:
            _evc = [(_evrow.get("latest"), "chapter")]
            _evc += [(_pv.get("last") or _pv.get("first"), "volume")
                     for _pv in (_evrow.get("print") or [])]
            _evc = [(d, k) for d, k in _evc if d]
            if not _evc:
                continue
            # Month against day: a volume states 2024-03 and a chapter states 2024-03-18, so the
            # comparison is made on the part both sides always carry.
            _evbest = max(_evc, key=lambda dk: (str(dk[0])[:7], str(dk[0])))
            _evrow["latest_any"], _evrow["latest_any_kind"] = _evbest
            if _evbest[1] == "volume" and _evbest[0] != _evrow.get("latest"):
                _anydate += 1
        print(f"rows whose most recent event is a volume rather than a chapter: {_anydate}")

        # WHERE THE SHOP DISAGREES WITH A PLATFORM, the platform wins and the disagreement is
        # counted rather than dropped. A shop marking a series 完結 while its serialisation is
        # still publishing is a finding about one of the two sources, and silently taking either
        # side would hide it. The claim rides only on rows where nothing else speaks.
        _claim_agree = _claim_clash = 0
        for _crow in series_rows:
            _held = [_pw.get(_cp["work_id"], {}).get("completed_claim")
                     for _cp in (_crow.get("print") or [])]
            if not any(_held):
                continue
            if _crow.get("state") in ("completed", "oneshot", "print"):
                _claim_agree += 1
            else:
                _claim_clash += 1
        if _claim_agree or _claim_clash:
            print(f"shop completion claims: {_claim_agree} agree with the state we hold, "
                  f"{_claim_clash} contradict a serialisation still running")

    # ── what a reader can check the record against ─────────────────────────────────────────────
    #
    # TWO LISTS, KEPT APART ON PURPOSE. `evidence` holds the sources that speak to whether the
    # work is yuri, ranked by credence.py and shown strongest first. `sourced_from` holds
    # everything else we read a source for: volume counts, dates, chapter counts. A volume count
    # says nothing about whether a work is yuri, and running the two together would make the
    # classification look better supported than it is by padding it with rows that answer a
    # different question.
    #
    # NOTHING HERE MARKS A SOURCE WITHDRAWN. adapters/reachable/ checks chapter pages and has
    # never been pointed at a basis page, so no row can honestly say a source has stopped carrying
    # a work. Each row states the day it was read and stops there. REQUIREMENTS §4 keeps the entry
    # either way, which is what the closing line of the section tells the reader.
    # THE CHAPTER ROWS ARE NOT COPIED HERE. `sources` on the same row already states each
    # platform, when it was read and where, so a second copy of it under another name would be two
    # producers of one fact and a megabyte of series.json besides. The page joins the two lists.
    _rec_by_wid = {_w5["work_id"]: _w5 for _w5 in works if _w5.get("work_id")}
    _ev_works = _ev_rows = _ev_mute = 0
    for _basisrow in series_rows:
        _got = list(_basisrow.get("evidence") or [])
        _held = []
        _labelled = _quoted = False
        for _bp in (_basisrow.get("print") or []):
            _brec = _rec_by_wid.get(_bp.get("work_id"))
            if not _brec:
                continue
            _from = credence.rows(_brec)
            _got += _from
            _labelled = _labelled or _brec.get("marketing_label") in ("yuri", "gl")
            _quoted = _quoted or any(_x["kind"] == "imprint" for _x in _from)
            _held += [{"source": credence.named(_bh["source"]), "holds": "volumes",
                       "read": _bh["retrieved"] or None,
                       **({"url": _bh["url"]} if _bh.get("url") else {})}
                      for _bh in (_brec.get("records") or [])]
            # A DELIVERY DATE IS ITS OWN FACT AND GETS ITS OWN ROW, naming the shop that stated it
            # and the day we read it. Without this the date reaches a reader through the 刊行 line
            # with nothing on the page saying whose date it is, and this is the table where every
            # other source of a date already says so.
            if _bp.get("delivered_from"):
                _drec = (_brec.get("records") or [{}])[0]
                _held.append({"source": credence.named(_drec.get("source") or ""),
                              "holds": "delivery-date",
                              "read": _drec.get("retrieved") or None,
                              **({"url": _bp["shop_url"]} if _bp.get("shop_url") else {})})
            # WHO SAYS THE BOOK IS BY THIS PERSON. A print row's credit is transcribed off the
            # bibliographic record, in the same `creator` field the roles came out of, so the
            # record that supplied the book supplied the byline and the row naming it is exact.
            if _basisrow.get("author") and (_brec.get("creator") or _brec.get("authors")):
                _crec = (_brec.get("records") or [{}])[0]
                if _crec.get("source"):
                    _held.append({"source": credence.named(_crec["source"]),
                                  "holds": "attribution",
                                  "read": _crec.get("retrieved") or None,
                                  **({"url": _crec["url"]} if _crec.get("url") else {})})
        # AND FOR A WEB WORK, THE PAGE THE BYLINE WAS ON. `author_src` recorded it beside the
        # credit as the sources were read, so the row cites the source that supplied the credit
        # this work actually carries rather than the first file to mention the title.
        _asrc = author_src.get(norm_work(_basisrow.get("work") or ""))
        if _basisrow.get("author") and _asrc and not any(
                _h.get("holds") == "attribution" for _h in _held):
            _held.append({"source": credence.named(_asrc["source"]), "holds": "attribution",
                          "read": _asrc.get("read") or None,
                          **({"url": _asrc["url"]} if _asrc.get("url") else {})})
        _basisrow["evidence"] = credence.order(_got)
        if _held:
            _basisrow["sourced_from"] = _held
        _ev_rows += len(_basisrow["evidence"])
        _ev_works += bool(_basisrow["evidence"])
        _ev_mute += bool(_labelled and not _quoted)
    print(f"categorisation evidence: {_ev_works} of {len(series_rows)} works carry at least one "
          f"row, {_ev_rows} rows in all; {len(series_rows) - _ev_works} carry none")
    # A LABEL WHOSE EVIDENCE THE RECORD DOES NOT HOLD. adapters/madb/extract.py picks VOLUMES whose
    # brand is one of the 百合姫 imprints and stores the SERIES record, whose own brand is often the
    # umbrella line IDコミックス. The label is right and the field a reader would be shown makes no
    # yuri claim, so the row is withheld rather than quoted. It clears when the extractor stores the
    # brand it selected on.
    if _ev_mute:
        print(f"publisher-side labels with no yuri imprint on the record to quote: {_ev_mute}")

    # AUTOPILOT. Before attaching anything, give every work and author the pipeline currently knows
    # about a reading if it does not have one. This is what makes a title that appears overnight
    # render in English by morning with nobody touching it — the alternative is a store that only
    # grows when someone remembers to run a pass, which is not a database that can be left running.
    #
    # Offline, idempotent, and additive only: a name with a reading from a real source is never
    # overwritten by a guess. If SudachiPy is not installed it does nothing and the interface falls
    # back to Japanese (§6), which is a documented state rather than a failure.
    # Bound before the block, because the naming helpers run inside a `try` that swallows anything
    # and the credit division below reads this whether or not they got that far. An empty map is
    # the honest degraded state: nothing is settled, so every ・ is treated exactly as it was.
    _credit_ruled = {}
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters" / "names"))
        import pass4_analyser as _p4
        # A TITLE THAT PRINTS ITS OWN READING IS ANSWERED BEFORE THE ANALYSER IS ASKED. The gloss
        # states what the analyser would otherwise guess, and it is right where the analyser is
        # wrong: 恋する小惑星 is said アステロイド and reads ショウワクセイ off the characters. The
        # gloss survives only at ingest, so `work_alias` wrote down what it removed and this is
        # where the second half of that fact is spent.
        _gl_written, _gl_disagreed, _gl_left = _gloss.fill_store(
            glossed_titles(), _p4.segment_reader())
        if _gl_written:
            print(f"names           : {len(_gl_written)} title(s) read as their own gloss prints "
                  f"them, {_gl_left} already answered")
        for _gl_title, _gl_held, _gl_want in _gl_disagreed:
            # NOT RESOLVED HERE. A reviewer settled one of these and a bracket states the other,
            # and a build has no standing to pick. Printed so it is a thing somebody looks at.
            print(f"names           : {_gl_title} is read {_gl_held!r} and its gloss "
                  f"says {_gl_want!r}")
        _p4.fill_missing({r["work"] for r in series_rows}, "titles")
        # THE PEOPLE, NOT ONLY THE FIELDS. The store holds one record per PERSON and this was fed
        # whole credit fields, which `is_credit_line` then declines to read, so nobody named only
        # alongside somebody else ever entered it. That is why 49 of 191 release rows rendered
        # their authors in Japanese on an English page: the composer had nothing to compose from.
        # The parts are added beside the fields, so a person credited only alongside somebody else
        # still gets a record of their own.
        #
        # AND FROM EVERY COLLECTION THAT CARRIES A CREDIT, WHICH IS WHAT `credit_fields` IS FOR.
        # This read `series_rows + releases`, which is the 更新 and 作品 tabs and nothing else, so
        # `index[].c` on the catalogue tab and `works[].creator` on the 発売 tab were never fed to
        # the pass at all: 579 people the interface renders had no record in the store, and the
        # number nowhere said so, because every measure of the naming work is taken over the store.
        # `credit_fields` already assembles the right set for the splitter, and it was sitting 280
        # lines below this call answering the same question for the division pass. Two producers of
        # one set, and the older one was the smaller (STANDING-INSTRUCTIONS §3).
        #
        # WITHOUT THE REGISTRY, WHICH IS NOT AVAILABLE YET. `credit_page_data` runs after this, and
        # the strings only the registry holds are joined fields like `iimAn&惟丞` that
        # `is_credit_line` refuses anyway, so nothing reaches the store through that argument.
        # WHERE AN INTERPUNCT SEPARATES PEOPLE AND WHERE IT IS A CHARACTER IN SOMEBODY'S NAME,
        # settled here because this is the first thing that needs it and everything below reuses
        # the answer (§3). `adapters/names/interpunct.py` reads the evidence only off credit fields
        # holding no ・ at all: `くろば・Ｕ` is one artist, nothing credits くろば or Ｕ alone, and
        # the store held both halves with a registry identifier each because the splitter that
        # filled it had already decided. A rule asking the store would agree with that split.
        _credit_ruled = _interpunct_rulings(credit_fields(idx, works, series_rows, releases))
        # INSTALLED ONCE, so nothing downstream has to remember to pass it. Of 31 splitter calls in
        # the project, 5 passed the ruling and 26 did not, which is how くろば・Ｕ came to be in the
        # store cut in half with an identifier on each piece.
        _credit_fact.use_rulings(_credit_ruled)
        _p4.fill_missing({p for f in credit_fields(idx, works, series_rows, releases)
                          for p in [f] + _credits.split_credits(f)[0] if p}, "authors",
                         ruled=_credit_ruled)
        # Chapter names and credit lines — 202 of the former against 6 titles, so this is most of
        # what stays Japanese on an English page.
        # Titles as phrases too, so one whose only Japanese is punctuation (IDOL×IDOL STORY！) is
        # covered; the title store keys on readings and skips those entirely.
        _p4.fill_chapters({x for r in releases + series_rows
                           for x in (r.get("ep"), r.get("latest_ep"), r.get("collection"),
                                     (r.get("author") or "").strip(),
                                     r.get("work")) if x}, ruled=_credit_ruled)
        # WHERE A PERSON'S NAME DOES NOT DIVIDE, and this runs FIRST because the answer it produces
        # is what the pass below is then allowed to ask a real source about. An analyser divides
        # every name it is handed, so のぴやか梢 was read ノ ピ ヤ カ コズエ and shown to an English
        # reader as `No Pi Ya Ka Kozue`, a claim about where a real person's name breaks that no
        # source makes. adapters/names/analyser_division.py takes out every space the surface does
        # not account for and keeps the ones it does.
        from facts import division as _adiv
        _fixed, _own = _adiv.retire_store()
        if _fixed:
            print(f"names           : {len(_fixed)} name(s) had a division an analyser invented "
                  f"and nothing states; {len(_own)} divide where their own surface says")

        # WHERE A KANA NAME DIVIDES. A reading is what the romanisation is built from, so a name
        # written in one unbroken run comes out as one word: いがらしゆみこ was Igarashiyumiko.
        # This carries a division some OTHER record for the same person states, which is offline,
        # additive and settles nothing it cannot cite. adapters/names/boundary.py holds the
        # argument, including the two rules that were tried and rejected.
        from facts import division as _boundary
        _cut, _left = _boundary.fill_store()
        if _cut:
            print(f"names           : {len(_cut)} kana name(s) divided from a record we already "
                  f"hold; {sum(_left.values())} left whole")

        # WHICH TITLES THE ANALYSER WAS ACTUALLY GUESSING AT. Every reading it produces is stamped
        # `verified: false` and the interface draws a `[?]`, and the note stored beside each one
        # says the doubt is about pen names and coinages. 私, 体, 風俗 and 百合 are none of those.
        # This asks the analyser what KIND of word it read rather than trusting its reading, and a
        # title whose every word is ordinary in-dictionary vocabulary keeps the reading and loses
        # the mark. adapters/facts/reading/vocabulary.py holds the rule and the three shapes that
        # keep the doubt.
        import analyser_vocabulary as _vocab
        _ord, _doubted = _vocab.apply_store()
        if _ord:
            print(f"names           : {sum(1 for v in _ord.values() if v)} title(s) read entirely "
                  f"in ordinary vocabulary; {sum(_doubted.values())} still guessed at")

        # PUBLISHERS TOO, and only the ones nothing else can reach. 32 publisher and imprint names
        # had no English at all, so 550 print rows named their publisher in Japanese beside an
        # English title, and hand-writing 32 romanisations would put a second spelling of 13 names
        # the author store already spells. `unreadable` asks both stores first for that reason, and
        # the queue it returns is the residue: labels and self-publishing circles nobody has
        # written a Latin name for anywhere.
        import publishers as _pubq
        _p4.fill_missing(_pubq.unreadable(_pubq.corpus_names_from_rows(series_rows),
                                          _pubq.load_store("data/names/publishers.yaml"),
                                          _pubq.load_store("data/names/authors.yaml")),
                         "publishers")
    except Exception as e:                      # never let a naming helper break the build
        print(f"names           : automatic reading pass skipped ({e})")

    # Attach English names and readings. Keyed on the exact Japanese string the store was built
    # from, so a work or author with no entry simply gets nothing and renders in Japanese (§6).
    _auth_names, _title_names, _pub_names = load_names()

    # A NAME AND ITS OWN READING ARE ONE PERSON. MADB states both in one schema:creator field
    # with a slash between them, and the slash is what separates two people, so 蓬餅 / ヨモギモチ
    # shipped as two credits. The source record keeps the field intact, because it says what
    # MADB said; the duplicate is collapsed here, where the credit is presented and where the
    # name store is loaded to settle the kanji cases.
    #
    # AND THE STORE IS NOT ENOUGH, which took a live report to establish. 田口ケンジ / タグチケンジ
    # shipped on w01478: the kana fold cannot see it because the name holds a kanji, and the store
    # cannot either because a CREDIT LINE is never fed to the naming pass, so neither half of the
    # field is in it. The analyser reads the name on demand instead. It can only ever collapse a
    # pair it read exactly onto its neighbour, so a misread name keeps both credits, which
    # test_credits.py proves by handing it a reader that returns マチガイ for every name.
    _authstore = (_auth_names if isinstance(_auth_names, dict) else {})
    try:
        _readname = _p4.reader()
    except Exception as _rerr:                  # never let a naming helper break the build
        print(f"names           : no reader for credit fields ({_rerr})")
        _readname = None
    _undoubled = _by_reader = 0
    for _credrow in series_rows:
        _was = _credrow.get("author") or ""
        if " / " not in _was:
            continue
        _deduped = _credits.dedupe(_was, _authstore, _readname)
        if _deduped != _was:
            _credrow["author"] = _deduped
            _undoubled += 1
            # How much of this the store could not have done, which is the number the budget on
            # the store-based measure was blind to.
            if _credits.dedupe(_was, _authstore) == _was:
                _by_reader += 1
    if _undoubled:
        print(f"credit fields holding a name beside its own reading: {_undoubled} collapsed "
              f"({_by_reader} of them only the analyser could see)")
    # WHAT IS LEFT, MEASURED WITHOUT THE STORE. A field with a katakana part beside a kanji part
    # has the shape of a name written twice whether or not anything can read either of them, so
    # this number cannot go green for the reason the last one did. It counts candidates rather
    # than faults: two people are written that way too.
    _still = sum(1 for _cd in series_rows
                 if _credits.candidate_doubles(_cd.get("author") or ""))
    print(f"credit fields still shaped like a doubled name: {_still} "
          f"(a candidate shape, not a fault; two people can be written that way)")


    # PUNCTUATION-TOLERANT LOOKUP. The store is keyed on the exact Japanese string, and the same
    # work reaches us with both （私に） and (私に) depending on the platform: full-width and
    # half-width brackets are different characters, so one variant matched and the other silently
    # got nothing. NFKC folds the two together without touching the words, so a lookup miss falls
    # back to the folded key rather than giving up.
    #
    # ONE PRODUCER OF THE KEY (§3). This was a closure here, `names/curate.py` had its own version
    # folding with NFKC alone, and `kari/app.js` has a third in JavaScript. So "is this the same
    # key" had two answers in Python, a measure written against the stricter one reported a number
    # the page contradicted, and it took a reader counting titles on a live page to find it.
    _fold = _namekey.fold

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

    # THE CATALOGUED SPELLING OF A TITLE IS THE SAME TITLE, and until now the map did not say so.
    # A cataloguer writes a subtitle after an ISBD colon and a platform writes it inside 〜 〜, so
    # `シャドウ・アサシンズ・ワールド : 影は薄いけど、最強忍者やってます` and
    # `シャドウ・アサシンズ・ワールド ～影は薄いけど、最強忍者やってます～` are one work under two
    # strings. The store is keyed on the platform's spelling, the 発売 tab and the catalogue draw
    # the record's, and folding normalises width and spaces and cannot join a colon to a tilde. So
    # eight works were rendered in English everywhere the series row is read and in Japanese on the
    # two tabs that read the bibliographic record.
    #
    # THE JOIN ALREADY EXISTS AND IS NOT GUESSED AT. `print[].work_id` is the record this row was
    # matched to, decided by identity.py against evidence, so this adds a key and no opinion. A
    # rule that stripped the subtitle instead would be a second producer of the title (§3) and
    # would answer for strings nothing has matched.
    #
    # AN EXISTING KEY IS LEFT ALONE. Where a catalogued spelling already has a record of its own,
    # that record was curated against that spelling and knows more than this does.
    _record_title = {w["work_id"]: ((w.get("title") or {}).get("ja") or "").strip()
                     for w in works if w.get("work_id")}
    _alias_titles = 0
    for r in series_rows:
        _row_cands = [x for x in (_title_names.get(r.get("work")),
                                  _title_folded.get(_fold(r.get("work")))) if x]
        if not _row_cands:
            continue
        _row_rec = max(_row_cands, key=_fullness)
        for _pr in (r.get("print") or []):
            _cat = _record_title.get(_pr.get("work_id")) or ""
            if not _cat or norm_work(_cat) in _wh_names:
                continue
            _cat_key = _fold(_cat)
            if _cat_key and _cat_key not in _title_folded:
                # MARKED AS AN ALIAS, and copied rather than shared, so a count over the shipped
                # file can tell one title held twice from two titles. `titles with no translation
                # of our own` rose by 2 the first time this ran, entirely because two records were
                # answering under a second key. The interface reads `en` and `romaji` and neither
                # notices the extra field.
                _title_folded[_cat_key] = dict(_row_rec, alias_of=_fold(r.get("work")))
                _alias_titles += 1
    if _alias_titles:
        print(f"titles          : {_alias_titles} catalogued spelling(s) keyed onto the record of "
              f"the work they name")

    _named_w = _named_a = 0
    for r in series_rows + releases:
        # AN EXACT MATCH IS NOT AUTOMATICALLY THE BETTER ONE. The same work reaches us spelled
        # 勝たん！～ and 勝たん!～, and the store holds a record for each: the curated one carries
        # the translation, the other only an automatic reading. Taking the exact hit first meant
        # whichever spelling the interface happened to display decided whether the work had an
        # English name at all. Both candidates are considered and the fuller wins, which is the
        # same rule fold_map already applies to records that fold together.
        # Named for what it is rather than reusing `_cands`, which is bound three hundred lines
        # above as the set of candidate work titles and is still live here.
        _name_cands = [x for x in (_title_names.get(r.get("work")),
                                   _title_folded.get(_fold(r.get("work")))) if x]
        t = max(_name_cands, key=_fullness) if _name_cands else None
        if t:
            r["work_en"] = t
            _named_w += 1
        _a_raw = (r.get("author") or "").strip()
        a = (_auth_names.get(_a_raw) or _auth_folded.get(_fold(_a_raw))
             or credits_en(_a_raw, _auth_names, _auth_folded, _fold))
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
    # EVERY TITLE THE BUILD KNOWS, STATED ONCE.
    #
    # Checks elsewhere need to ask "is this a work we hold", and the only way to ask it was to
    # reassemble the corpus from artefacts that were never meant to answer it: the feed's rolling
    # window, which forgets a work after a fortnight; the month archives, which hold events rather
    # than works; series.json, which drops rows the interface will not show. Three of them together
    # still missed 18 works and disagreed with a fourth about punctuation. A load-bearing question
    # deserves a stated answer rather than an inference from leftovers.
    #
    # AS THE BUILD HOLDS THEM, not folded. Two consumers fold differently on purpose: the name
    # lookup here drops spaces so a title joins whatever spacing a platform used, and curate.py
    # keeps them so a curated key with a stray space stays a typo somebody can find. An artefact
    # that had already folded would settle that argument for both of them by accident.
    _known_titles = set()
    for _row in series_rows:
        if _row.get("work"):
            _known_titles.add(_row["work"])
    for _rel in releases:
        if _rel.get("work"):
            _known_titles.add(_rel["work"])
        if _rel.get("collection"):
            _known_titles.add(_rel["collection"])
    for _wk in works:
        _ja = (_wk.get("title") or {}).get("ja")
        if _ja:
            _known_titles.add(_ja)
    (out / "titles.json").write_text(json.dumps(
        {"generated": str(_today),
         "note": "Every title this build knows, as it holds them. The answer to 'is this a work "
                 "we hold', stated here rather than reassembled from the feed window, the month "
                 "archives and the series list, none of which is the corpus. Fold as you need: "
                 "consumers disagree about spaces on purpose.",
         "count": len(_known_titles),
         "titles": sorted(_known_titles)}, ensure_ascii=False, indent=1))
    print(f"titles known to this build: {len(_known_titles)}")

    # A COMPANY NAME IS A NAME, so it ships beside the other two instead of in a file of its own.
    _pub_shipped = publisher_map(_pub_names, _auth_folded, series_rows)
    _pub_romanised = sum(1 for v in _pub_shipped.values() if v.get("basis") == "romaji")
    print(f"publishers      : {len(_pub_shipped)} key(s) with an English name in feed/names.json, "
          f"{_pub_romanised} of them a romanisation")

    # AN IMPRINT IS ONE OBJECT WITH MANY RECORDED SPELLINGS, and the field holds the spellings.
    _imp_shipped = imprint_map(series_rows)

    # A LINE'S CANONICAL NAME IS A NAME A READER MEETS, so it needs a rendering like any other.
    # The publisher pass ran against the CATALOGUED spellings, and the registry then chose a
    # canonical name for each line, so eleven names that reach the page had never been offered for
    # naming: ハルタコミックス, FUZコミックス, まんがタイムKRコミックスつぼみシリーズ and the MF
    # series among them. They are keyed here so the same lookup answers for them, raw and folded
    # alike, which is the rule the publisher map already follows.
    #
    # THE SKIP ASKS WHAT THE READER'S LOOKUP ASKS, and asking anything else is what hid
    # MFC キューンシリーズ for a round. `pubRec` in app.js tries the string and its NFKC form and
    # does not remove spaces; this tested the space-stripped fold, found the catalogued
    # `MFCキューンシリーズ` already in the map, and concluded the line was named. It was named under
    # a key nothing asks for, so 35 rows showed the line in Japanese in English-only mode
    # (STANDING-INSTRUCTIONS §14b: a producer's "do I have this already" must be the consumer's
    # lookup, or it answers a question nobody is asking).
    sys.path.insert(0, str(pathlib.Path(__file__).parent / 'adapters' / 'names'))
    import publishers as _pubmod
    _imp_named = 0
    for _fact in {id(v): v for v in _imp_shipped.values()}.values():
        _nm = (_fact or {}).get("name")
        if not _nm or _nm in _pub_shipped or unicodedata.normalize("NFKC", _nm) in _pub_shipped:
            continue
        _one = _pubmod.render(_pub_names, _auth_folded,
                              {("imprint", _nm): {"kind": "imprint", "raw": _nm,
                                                  "shown": _nm, "volumes": 1}})
        _rendered = _one.get(_nm) or _one.get(_fold(_nm))
        if _rendered:
            _pub_shipped.setdefault(_nm, _rendered)
            _pub_shipped.setdefault(_fold(_nm), _rendered)
            _imp_named += 1
    if _imp_named:
        print(f"imprints        : {_imp_named} line name(s) given a rendering of their own")
    _imp_lines = len({v["id"] for v in _imp_shipped.values()})
    print(f"imprints        : {_imp_lines} line(s) answering {len(_imp_shipped)} key(s) in "
          f"feed/names.json")

    # BUILT BEFORE THE NAME MAP IS WRITTEN, because the credit registry holds spellings no feed
    # row does and each of them needs a division shipped beside the rest. The file itself is
    # written further down with the other record page.
    _credits_shipped = credit_page_data(series_rows)

    # THE DIVISION OF EVERY CREDIT FIELD A READER CAN MEET. Computed here because it needs the
    # author store, which is what tells a reading printed beside a name from a second artist.
    #
    # AND THE INTERPUNCT IS SETTLED OFF THE FIELDS THEMSELVES, not off the store. The rule was
    # "divide where both halves are names the map can render", and the map holds くろば and Ｕ
    # because the name-store splitter cut that person in half, so the test agreed with the split
    # that produced it and `Kuro Ba, U` went to a reader (STANDING-INSTRUCTIONS §14b).
    # `interpunct.settled` reads the evidence off credit fields holding no ・ at all, which is 8,812
    # of the 8,865 here and none of the ones under question.
    _credit_fields = credit_fields(idx, works, series_rows, releases, _credits_shipped)
    _credit_div = {}
    _credit_unaccounted = 0
    for _cf in _credit_fields:
        _cd = credit_parts(_cf, _auth_folded, _credit_ruled)
        if not _cd:
            continue
        _credit_div[_fold(_cf)] = _cd
        _credit_unaccounted += 1 if _cd.get("part") else 0
    print(f"credits         : {len(_credit_div)} field(s) divided for the interface, "
          f"{_credit_unaccounted} not fully accounted for")

    # BUILT HERE RATHER THAN BESIDE ITS OWN FILE, because the floor below is asked what a publisher
    # page shows and that answer exists only in this document. The write is further down with the
    # other record page.
    _houses_shipped = publisher_page_data(series_rows)

    # ── THE FLOOR UNDER AN ENGLISH PAGE ───────────────────────────────────────────────────────
    #
    # THE OWNER'S RULING. A name the store cannot render used to show as the Japanese, and 77 rows
    # were doing so. That is now the one thing an English page may not do: where nothing states how
    # a name is read, the page shows a mechanical romanisation and marks it. `adapters/names/
    # romfloor.py` spells them and this ships the answer.
    #
    # SPELLED HERE AND LOOKED UP THERE. `kana.romanise` is the project's one romanisation, and a
    # second copy of it in JavaScript is the shape §3 counts seven shipped bugs from. The browser
    # decides nothing about spelling; it reads this map.
    #
    # WHAT IT COVERS, ASKED OF THE ONE TABLE THAT KNOWS. `adapters/interface.py` says which field is
    # rendered by which function, and `calls_for` walks every value of every one of them. Reading
    # that table here is what keeps the floor total without a second list going stale: a surface
    # added there is floored without anybody remembering to.
    #
    # AND THE RUNS INSIDE EACH STRING, because a credit field is rendered IN PLACE. `BPS株式会社`
    # sits between two rendered names in a field nothing divided, so the map has to answer for the
    # run as well as for the field.
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "adapters"))
    import interface as _ifacemod
    import romfloor as _romfloor
    _floor_cols = {"index": idx, "series": series_rows, "works": works, "releases": releases,
                   "credits": list((_credits_shipped.get("credits") or {}).values()),
                   "publishers": list((_houses_shipped.get("publishers") or {}).values()),
                   "status": []}
    _floor_want = {v for _s, v in _ifacemod.calls_for(_floor_cols)[1]}
    _floor_want |= {p["n"] for _d in _credit_div.values()
                    for p in (_d.get("p") or []) if p.get("n")}
    # The store's own keys, because `nameFor` is asked with the string a row carries and a record
    # can hold a reading the interface still declines to show.
    for _m in (_auth_folded, _title_folded, _pub_shipped, _imp_shipped):
        _floor_want |= set(_m)
    _floor, _floor_unread = _romfloor.build(_floor_want, floor_reader(), runs_of=_credit_fields)
    print(f"floor           : {len(_floor)} string(s) spelled for the English fallback, "
          f"{len(_floor_unread)} nothing could read")

    (out / "feed" / "names.json").write_text(json.dumps(
        {"generated": str(_today),
         "note": "English renderings and readings, keyed by NFKC-folded title/author. Joined onto "
                 "feed rows at render time so archived months — which are never rewritten — still "
                 "show current names.",
         "titles": _title_folded, "authors": _auth_folded,
         # PUBLISHERS AND IMPRINTS, keyed by the string the catalogue holds and by the string the
         # interface shows. `basis` says whose name it is: official-jp is the company's own and is
         # shown unmarked, romaji is a Latin form of the Japanese and is ours.
         "publishers": _pub_shipped,
         # WHICH LINE A CATALOGUED IMPRINT STRING NAMES, keyed by the string and by its fold. The
         # value carries the line's own name and the umbrella it sits inside where it has one, so a
         # reader looking at a 2008 volume sees what that volume says and still learns which line it
         # is. A string the registry does not answer for is absent here, which is a state and not a
         # gap: the interface keeps showing the catalogued string.
         "imprints": _imp_shipped,
         # Chapter names, collections and credit lines, keyed folded like the rest.
         # phrases carries collection and chapter names, and a withheld work's title lands here
         # too when it names a collection. Filtered on the same register.
         # phrases carries collection and chapter names, and a withheld work's title lands here
         # too when it names a collection. Same register, or the title ships anyway.
         # A CREDIT LINE IS COMPOSED FROM THE PEOPLE IN IT. The phrase map is written once per
         # string by the analyser and never revisited, so it romanises the whole line as one run
         # and no later correction reaches it: 入間人間 has a sourced reading of イルマ ヒトマ and
         # its credit line still read "Iruma Ningen"; 柚原もけ came out "Yuhara mo Ke" because the
         # analyser broke a name it had never seen. Recomposed from the store, from a name already
         # in Latin, and from the floor, in that order, and left alone only where a name defeats
         # all three.
         # The people in each credit line, keyed like the phrases, so the interface can render a
         # line from its parts and follow the reader's romanisation style and name order. The
         # composed phrase stays as the fallback for a line whose people we do not all know.
         "credit_parts": _credit_div,
         # THE LAST THING AN ENGLISH RENDERING FALLS BACK TO, in the reader's three styles like
         # every other romanisation. Keyed by the same fold as the rest, on the whole string and on
         # each Japanese run inside it. A key here does NOT mean the interface will use it: a name
         # with a reading is spelled from the reading, and this answers only where nothing else can.
         "floor": _floor,
         # THE FLOOR TRAVELS WITH IT, because a field naming one person also carries the job that
         # person did, and the job has to be spelled by the map the rest of the site spells from.
         #
         # THE FOLDED STORE, WHICH IS THE MAP `credit_parts` IS BUILT AGAINST. This was handed the
         # raw-keyed store while the division beside it was resolved against `_auth_folded`, so a
         # person the splitter names as 王月 よう and the store files as 王月よう was a lookup miss
         # here and a hit there. Eight credit fields kept the analyser's spelling on the strength
         # of a space, and the budget counting them read that as a residue of the composition rule.
         # One key, one map (§3).
         #
         # `divided` SAYS THE PARTS ARE PEOPLE, and it is the counter-case that nearly shipped.
         # This map holds chapter names and collection titles beside credit lines, and the old bar
         # kept the recomposition off them by accident: it declined whenever a part was missing
         # from the author store, and no store holds のけもののまち. Spelling a missing part from
         # the floor removes that accident, and letting it answer everywhere rewrote 1,573 titles
         # and chapter names, `月はタピオカみたいに` as `Tsuki Wa Tapioka Mitaini` with the particle
         # capitalised and `特別編4` as `Tokubetsuhen4` with a translation thrown away.
         #
         # `_credit_div` is the build's own statement that this string is a credit field and here
         # is how it divides, which is the fact this needs and one nothing else has to derive. A
         # string outside it keeps the old bar, so the 201 fields the store already recomposes are
         # untouched.
         "phrases": {_fold(k): _recompose_credit(k, v, _auth_folded, _credit_ruled, _floor,
                                                 _fold(k) in _credit_div)
                     for k, v in (
             (yaml.safe_load(pathlib.Path("data/names/phrases.yaml").read_text()) or {}
              ).get("names", {}) if pathlib.Path("data/names/phrases.yaml").exists() else {}
         ).items() if norm_work(k) not in _wh_names}},
        ensure_ascii=False, indent=1, default=jsonable))

    # ── the two records that are not works ────────────────────────────────────────────────────
    #
    # A CREDIT PAGE AND A PUBLISHER PAGE NEED WHAT NO OTHER FILE CARRIES. `series.json` holds a
    # credit as a STRING and a publisher as a field on a print row, so an interface asking "what
    # else did this person make" or "which of this house's lines are yuri" would have to split
    # every credit field and resolve every imprint spelling in the browser. Both of those rules
    # already exist in Python and §3 says the second implementation will disagree with the first.
    #
    # SO THE ANSWER SHIPS, and the registry modules are the only things that compute it. These are
    # fetched when a reader opens one of these pages and never for an ordinary visit, which is why
    # they are separate files rather than more keys on `names.json`: that one loads on every visit.
    (out / "credits.json").write_text(json.dumps(_credits_shipped, ensure_ascii=False, indent=1,
                                                 default=jsonable))
    _cp_n = len(_credits_shipped.get("credits") or {})
    _cp_e = sum(len(v.get("works") or []) for v in (_credits_shipped.get("credits") or {}).values())
    _cp_r = sum(1 for v in (_credits_shipped.get("credits") or {}).values()
                for w in (v.get("works") or []) if w.get("roles"))
    print(f"credit pages    : {_cp_n} record(s), {_cp_e} edge(s) to works, {_cp_r} of them "
          f"naming a role")

    (out / "publishers.json").write_text(json.dumps(_houses_shipped, ensure_ascii=False, indent=1,
                                                    default=jsonable))
    _hp = _houses_shipped.get("publishers") or {}
    print(f"publisher pages : {len(_hp)} house(s), "
          f"{sum(len(v.get('lines') or []) for v in _hp.values())} line(s) across them")

    # WHERE A RETIRED IDENTIFIER WENT, shipped so the interface can follow it. An address published
    # once has to keep resolving, which is why an id here is opaque and minted; the registry has
    # recorded `merged_into` since the beginning and nothing outside identity.py read it, so a work
    # page asked for a retired id rendered a blank page.
    _merged = {}
    _idreg2 = pathlib.Path("data/identity/works.yaml")
    if _idreg2.exists():
        for _e3 in (yaml.safe_load(_idreg2.read_text()) or {}).get("works") or []:
            if _e3.get("merged_into"):
                _merged[str(_e3["id"])] = str(_e3["merged_into"])

    (out / "series.json").write_text(json.dumps(
        {"series": series_rows,
         "merged": _merged,
         "generated": str(_today),
         # WHERE EACH EVIDENCE RANK CAME FROM, once per file rather than once per row. Every
         # `evidence` row names its kind and its rank; this says which clause of DEFINITIONS and
         # REQUIREMENTS put that kind where it is. Nothing renders it, and it is published because
         # a reader of the data should be able to check the ordering against the documents.
         "credence": credence.RULE,
         "note": "Built from full chapter histories in data/source/, not from the 60-day feed "
                 "window. One row per WORK; its platforms are listed as sources, because they "
                 "differ in coverage rather than in what they are.",
         "thresholds": {"active": "latest chapter within 45 days",
                        "slow": "within a year", "dormant": "older than a year"}},
        ensure_ascii=False, indent=1, default=jsonable))
    _st = Counter(r["state"] for r in series_rows)
    if shelf_cited:
        print(f"shelf citations : {shelf_cited} comparator entries cite the shelf the claim is on, "
              f"{shelf_paged} of them the page it was read from")
    if undated_works:
        print(f"undated works   : {undated_works} recorded with no attested publication date")
        # WHICH SILENCE, because a total says how far there is to go and nothing about how to get
        # there. `no-print-edition` is finished work and no pass will move it: a web serial that
        # later gets a tankōbon leaves this count, but that arrives from a capture finding the
        # printing and not from working the gap. `no-date-attested` is the one nobody has an
        # answer for and is what a later pass should be aimed at.
        for _basis_name, _basis_n in sorted(undated_by_basis.items(), key=lambda kv: -kv[1]):
            print(f"    {_basis_n:5}  {_basis_name}")
    _dtally = delivery.tally(series_rows)
    if _dtally["rows"]:
        print(f"delivery dates  : {_dtally['rows']} works dated by the day a shop began delivering "
              f"the file, because no paper record is reachable")
        # NOT A BACKLOG, AND THE SPLIT IS WHY. `no-earlier-record-expected` is finished work under
        # DEFINITIONS §6, `unclassified` means the shop said nothing about the edition, and only
        # `earlier-edition-unsourced` is a row a better source could answer.
        for _dk_name, _dk_n in sorted(_dtally["followup"].items(), key=lambda kv: -kv[1]):
            print(f"    {_dk_n:5}  {_dk_name}")
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

    # THE WORK'S OWN IDENTIFIER ON EVERY UPDATE, so a row in the feed can offer the record of the
    # work it is an instalment of. The feed is keyed by CHAPTER and knew only the chapter's address,
    # so the updates tab could send a reader to the platform and nowhere else.
    #
    # Runs after the identity pass above, which is what puts an id on a series row in the first
    # place. Matched on the title AND the platform where both are known, because a normalised title
    # is not an identifier: where two works share one and no platform separates them, the row gets
    # no id rather than a guess at which work it belongs to. That is identity.py's own rule about a
    # contested anchor, applied to the same question from the other side.
    _wid_by_work, _wid_ambiguous = {}, set()
    for _wrow in series_rows:
        if not _wrow.get("id"):
            continue
        _wkey = norm_work(_wrow.get("work"))
        if _wid_by_work.get(_wkey) not in (None, _wrow["id"]):
            _wid_ambiguous.add(_wkey)
        _wid_by_work.setdefault(_wkey, _wrow["id"])
        for _wsrc in (_wrow.get("sources") or []):
            _wid_by_work.setdefault((_wkey, _wsrc.get("platform")), _wrow["id"])
    _wid_linked = 0
    for _frow in releases:
        _wkey = norm_work(_frow.get("work"))
        _found = _wid_by_work.get((_wkey, _frow.get("plat")))
        if not _found and _wkey not in _wid_ambiguous:
            _found = _wid_by_work.get(_wkey)
        if _found:
            _frow["wid"] = _found
            _wid_linked += 1
    print(f"updates carrying their work's identifier: {_wid_linked} of {len(releases)}"
          f"{f'; {len(_wid_ambiguous)} title(s) shared by more than one work' if _wid_ambiguous else ''}")

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
    # THE CHECKS ARE A THIRD OF THE BUILD: 34 s of 94 s, measured. Most builds during an edit are
    # run for the data alone, and the checks that matter at that moment get run separately a moment
    # later. `--no-checks` skips them and says so, and it leaves `checks.json` and `status.json` as
    # the last full build left them, which is why the invariant reading them is not weakened: it
    # compares the DEPLOYED copy against the BUILT one, and `deploy.sh` is downstream of a full run.
    #
    # NOTHING THAT BLOCKS IS SKIPPED. The pre-commit and pre-push hooks run `check.py --gate`, which
    # ignores this flag entirely, so the fast path exists only between a person and their next
    # keystroke.
    # THE DEFAULT IS NOW TO SKIP THEM. The flag existed and went unused, which is a sign the
    # default was wrong: a build during an edit is run for the data, and the checks that matter at
    # that moment are run a moment later by the gate. `--checks` asks for them; the hooks run
    # `check.py --gate`, which ignores both flags, so nothing that blocks is affected.
    if "--checks" not in sys.argv:
        print("checks          : skipped (pass --checks to run them; the gate runs them anyway)")
    else:
        try:
            import subprocess as _sp
            sys.stdout.flush()      # the child writes straight to the fd; without this its output
                                    # lands ahead of the build's own buffered lines and reads as
                                    # though the checks ran before the thing they check.
            _sp.run([sys.executable, str(pathlib.Path(__file__).parent / "check.py"), "--runtime"],
                    timeout=180)
        except Exception as _e:
            print(f"checks          : could not run ({_e})")


if __name__ == "__main__":
    main()
