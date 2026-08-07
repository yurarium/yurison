#!/usr/bin/env python3
"""Who a platform says drew a work, for the works our corpus credits to nobody.

WHY THIS EXISTS. 103 works in the corpus name no author, and not one of them is anonymous: the
platform prints the byline at the top of the page it publishes the work on. The gap is ours. Six of
the web platforms were read by adapters written to answer a different question, which is when
each chapter appeared. A chapter list has no room for a fact about the work, so the byline beside
the title was walked past. build.py already reads an author off any source record that carries one
(`author_of`), so the whole of the fix is a record that carries one.

WHAT A BYLINE IS HERE. The name the platform prints, with the role label it prints beside it kept
as a role and not as part of the name. `原作：緋月紫砲` is one person called 緋月紫砲 credited as
the writer, and a reader that took the string whole invented a person named 原作：緋月紫砲. The
same shape reaches us from pixivコミック as one string with its own separators
(`漫画：白梅ナズナ／原作：まきぶろ`), so splitting is done here rather than left to the name passes,
which see a finished credit and cannot tell a label from a surname.

WHY EACH SHAPE IS NAMED RATHER THAN GUESSED. A generic "find the author-ish element" pass over
these pages returns the platform's search placeholder (`作品名・作者名を入力してください`), its
footer link to the author index, and the bylines of every recommended work in the sidebar. Every
one of those is a string that looks exactly like an answer. So a shape is only used where a page
was read and the shape proven on it, and a page matching no shape returns nothing rather than
something plausible: SHAPES below is the whole list, and `unreadable` is a first-class outcome.

WHAT IS DELIBERATELY NOT HERE.

  THE DESCRIPTION TAIL. マンガワン states no byline in any element, and appends the artist to the
  end of its `<meta name="description">` after the synopsis: `…青春群像劇。 南文夏`. That is the
  platform stating the name, and reading it means assuming the last run of characters after the
  last full stop is a person. On a synopsis ending in a character's name it is not. Those works are
  reported unreadable and settled by hand against a second source.

  BOOK☆WALKER'S CREDIT LIST. The shop credits every work it sells, and using it here would settle
  the corpus's author from the same page a pending join is waiting to be compared against. The join
  would then agree with itself and a reviewer would be shown two copies of one claim. コミックシーモア
  is read instead, for exactly that reason: it is the other shop, it lists a whole contributor
  line-up where BOOK☆WALKER truncates to `著者: みんたろう 他`, and a reviewer comparing the two
  is comparing two independent statements. See `from_shelf`.
"""
import html as _html
import json
import re

# ── the shapes, each proven against a page in the fixture set ────────────────────────────────────

# comicブースト: the work's own byline is the FIRST author-list after the work's h1. The page then
# repeats the shape for every recommended work below, so the search is anchored on the title.
BOOST_TITLE = re.compile(r'<h1 class="comic-title">')
BOOST_LIST = re.compile(r'<ul class="author-list">(.*?)</ul>', re.S)
BOOST_ITEM = re.compile(r'<li class="author">(.*?)</li>', re.S)

# ヤンマガWeb: the series page, not the episode page. `detailv2-outline-author` is the work's own
# and appears once; the sidebar uses different class names.
YANMAGA = re.compile(r'<ul class="detailv2-outline-author">(.*?)</ul>', re.S)

# マンガPark: `<p class="author txtColorSubject">` directly after the work's h1. The class is used
# again further down for the synopsis, so the paragraph is matched with `author` in it, first only.
PARK = re.compile(r'<p class="author[^"]*">(.*?)</p>', re.S)

TAG = re.compile(r"<[^>]+>")

# Every word these platforms use for what a person did. Held as a vocabulary rather than as two
# patterns because the LABEL AND THE NAME ARRIVE IN EITHER ORDER, sometimes on one page: マンガPark
# writes `原作：来須みかん　漫画：霜月かいり` on one work and `御坊：原案監修　丸山ゴンザレス：協力`
# on the next. A rule fixing the label to one side of the colon reads half of them backwards and
# publishes a person called 原案監修. So the side that IS a role word is the role, whichever it is,
# and a colon with a role word on neither side is left alone.
ROLES = ("キャラクターデザイン", "キャラクター原案", "キャラ原案", "取材協力", "原案監修",
         "原作", "作画", "漫画", "イラスト", "構成", "脚本", "企画", "監修", "原案", "編集",
         "協力", "著", "作")
ROLE = re.compile(r"^\s*(?:" + "|".join(ROLES) + r")\s*$")

# A role written after a name in brackets, which is ファイアCROSS's shape: `夏河もか（漫画）`.
ROLE_SUFFIX = re.compile(r"[（(]\s*(?:" + "|".join(ROLES) + r")\s*[）)]\s*$")

# What separates two credits inside one string. pixivコミック uses ／, MADB and the shops use /.
CREDIT_SPLIT = re.compile(r"\s*[／/]\s*")

# WHITESPACE IS ONLY A SEPARATOR WHERE THE STRING IS LABELLED. マンガPark runs several credits
# into one paragraph and separates them with an ideographic space, and 宮原　都 is one person whose
# name contains one. Splitting on the space unconditionally cuts that person in half; splitting
# only when the string carries a role colon leaves an unlabelled paragraph whole, which records
# the platform's own string rather than a guess about how many people are in it.
SPACE_SPLIT = re.compile(r"[\s　]+")


def text(fragment):
    """Markup with its tags removed and its entities resolved, layout whitespace collapsed.

    THE IDEOGRAPHIC SPACE IS NOT LAYOUT. 宮原　都 writes their name with one in it, and every other
    source in this corpus holds it that way, so collapsing `\\s+` turns one person into a second
    spelling of themselves that joins to nothing. Only the whitespace a markup indent produces is
    collapsed.
    """
    return re.sub(r"[ \t\r\n\f\v]+", " ",
                  _html.unescape(TAG.sub("", fragment or ""))).strip()


def one_credit(s):
    """`(name, role)` for a single credit, with the role label taken off the name.

    A NAME IS WHAT IS LEFT WHEN THE LABEL IS GONE, and nothing else is stripped. `白梅ナズナ` keeps
    its characters; only a role word on one side of a colon, or a role word alone in brackets at
    the end, is removed. Anything else in brackets is part of the name.
    """
    s = (s or "").strip()
    role = ""
    if "：" in s or ":" in s:
        left, right = (p.strip() for p in re.split(r"[:：]", s, maxsplit=1))
        if ROLE.match(left):
            role, s = left, right
        elif ROLE.match(right):
            role, s = right, left
    m = ROLE_SUFFIX.search(s)
    if m:
        role, s = role or m.group(0).strip("（）() "), s[:m.start()].strip()
    return s.strip(), role


def credits(s):
    """`[(name, role)]` for a byline string that may carry several credits."""
    parts = CREDIT_SPLIT.split(s or "")
    if len(parts) == 1 and ("：" in s or ":" in s):
        parts = SPACE_SPLIT.split(s.strip())
    out = []
    for part in parts:
        name, role = one_credit(part)
        if name:
            out.append((name, role))
    return out


def _jsonld_blocks(page):
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page or "", re.S):
        try:
            yield json.loads(m.group(1))
        except ValueError:
            continue


def _authors_in(node, out):
    """Every `author` a schema.org graph names, depth-first. Nested because a page may wrap its
    Book in an @graph, a list, or both, and the author sits at a different depth in each."""
    if isinstance(node, dict):
        a = node.get("author")
        if isinstance(a, dict):
            a = [a]
        for one in a if isinstance(a, list) else []:
            if isinstance(one, dict) and (one.get("name") or "").strip():
                out.append(one["name"].strip())
        for v in node.values():
            _authors_in(v, out)
    elif isinstance(node, list):
        for v in node:
            _authors_in(v, out)
    return out


def _publishers_in(node, out):
    if isinstance(node, dict):
        p = node.get("publisher")
        for one in (p if isinstance(p, list) else [p]):
            if isinstance(one, dict) and (one.get("name") or "").strip():
                out.append(one["name"].strip())
        for v in node.values():
            _publishers_in(v, out)
    elif isinstance(node, list):
        for v in node:
            _publishers_in(v, out)
    return out


def from_jsonld(page):
    """Bylines from schema.org `author`, which ファイアCROSS, GANMA! and COMIC熱帯 all publish.

    The standard field, so it is tried first and is the only shape that is not site-specific. It
    also carries the role inside the name on ファイアCROSS (`夏河もか（漫画）`), which `credits`
    takes off.

    A COMPANY IN THE AUTHOR FIELD IS STILL A COMPANY. ナナシの転生 is adapted from a franchise
    ホビージャパン owns, and ファイアCROSS credits `ホビージャパン（原作）` beside the two artists,
    as a `Person`. Recorded as an author it becomes a pen name for the reading passes to work on,
    beside the artists who actually drew the book. The record answers this about itself: the same
    graph names ホビージャパン as the publisher, and a credit that is the publisher's own name is
    the rights holder. Nothing is inferred from the shape of the name.
    """
    got = []
    for block in _jsonld_blocks(page):
        _authors_in(block, got)
    houses = []
    for block in _jsonld_blocks(page):
        _publishers_in(block, houses)
    out = []
    for s in got:
        for name, role in credits(s):
            if any(name and name in h for h in houses):
                continue
            if (name, role) not in out:
                out.append((name, role))
    return out


def from_comicboost(page):
    """comicブースト's own byline: the first `author-list` at or after the work's `comic-title`."""
    anchor = BOOST_TITLE.search(page or "")
    if not anchor:
        return []
    m = BOOST_LIST.search(page, anchor.end())
    if not m:
        return []
    out = []
    for item in BOOST_ITEM.findall(m.group(1)):
        for pair in credits(text(item)):
            if pair not in out:
                out.append(pair)
    return out


def from_yanmaga(page):
    """ヤンマガWeb's series page byline."""
    m = YANMAGA.search(page or "")
    if not m:
        return []
    out = []
    for item in re.findall(r"<li[^>]*>(.*?)</li>", m.group(1), re.S):
        for pair in credits(text(item)):
            if pair not in out:
                out.append(pair)
    return out


def from_pixivcomic(payload):
    """pixivコミック's byline, from the catalogue API the site's own front end calls.

    The work page is drawn in the browser and carries no byline in its markup, so the page is not
    what is read. `works/v5/<id>` returns `author` as one string with every credit and its label in
    it, which `credits` splits.
    """
    try:
        d = json.loads(payload or "")
    except ValueError:
        return []
    work = (d.get("data") or {}).get("official_work") or {}
    return credits(work.get("author") or "")


def from_mangapark(page):
    """マンガPark's byline, the first `author` paragraph on the page.

    The work's own is first and every later one belongs to a recommended work, which is why this
    takes one and not all: taking all credited 天乃忍 with a work she did not draw.
    """
    m = PARK.search(page or "")
    return credits(text(m.group(1))) if m else []


# Host to shape. A host absent from here is not read, which is the point: nothing is parsed
# speculatively, and a work on an unlisted host is reported rather than guessed at.
SHAPES = {
    "comic-boost.com": from_comicboost,
    "yanmaga.jp": from_yanmaga,
    "manga-park.com": from_mangapark,
    "firecross.jp": from_jsonld,
    "ganma.jp": from_jsonld,
    "www.comicnettai.com": from_jsonld,
    "comic.pixiv.net": from_pixivcomic,
}

# ヤンマガWeb's work URLs reach us with the episode hash on the end, and the byline is on the
# series page. 32 hex characters is the episode id; the segment before it is the work.
EPISODE_HASH = re.compile(r"^[0-9a-f]{32}$")
PIXIV_WORK = re.compile(r"^https://comic\.pixiv\.net/works/(\d+)")

# pixivコミック's API asks for this, and it is the one header the endpoint is specifically fed.
PIXIV_HEADERS = {"X-Requested-With": "pixivcomic",
                 "Referer": "https://comic.pixiv.net/",
                 "Origin": "https://comic.pixiv.net"}


def series_url(url):
    """What to read for this work: its own page, or the endpoint that states what the page draws.

    Kept in one function because the answer is one thing, which is where the byline is. Splitting
    it into "the page" and "the API" would give two callers two chances to disagree about which
    host needs which.
    """
    u = (url or "").strip()
    if u.startswith("https://yanmaga.jp/comics/"):
        parts = u.rstrip("/").split("/")
        if EPISODE_HASH.match(parts[-1]):
            return "/".join(parts[:-1])
    m = PIXIV_WORK.match(u)
    if m:
        return f"https://comic.pixiv.net/api/app/works/v5/{m.group(1)}"
    return u


def host_headers(url):
    """Whatever a host requires beyond the User-Agent."""
    return dict(PIXIV_HEADERS) if host_of(url) == "comic.pixiv.net" else {}


def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower() if m else ""


def byline(url, page):
    """`[(name, role)]` the platform states for this work, empty where no shape reaches it."""
    shape = SHAPES.get(host_of(url))
    return shape(page) if shape else []


# WHAT A SHOP WRITES IN THE AUTHOR SLOT WHEN THERE IS NO SINGLE AUTHOR. コミックシーモア files 29
# rows under `アンソロジー`, which is the word "anthology": it says what the book is and names
# nobody. Recorded as a credit it becomes a prolific pen name with 29 works and a reading, which is
# the same failure as crediting a doujin circle as a person. `編集部` is the other one, and it is
# the publisher's editorial department rather than a placeholder, so it is kept as the credit the
# shop gives and marked, not dropped.
NOT_A_PERSON = ("アンソロジー", "アンソロジーコミック", "オムニバス", "各種", "著者不明")
A_GROUP = re.compile(r"編集部$|編集室$|製作委員会$")


def shelf_credits(rows, title_key, want, shop="cmoa.jp"):
    """`[name]` one shop lists for a work, dropping what is not a name at all.

    ROWS FROM ONE SHOP ONLY, named by the caller. A line-up assembled from two shops would agree
    with whichever it was later compared against, which is the thing `bw-review.yaml` is waiting
    for a person to judge.
    """
    out = []
    for r in rows:
        if (r.get("shop") or "") != shop or title_key(r.get("title") or "") != want:
            continue
        for name in (r.get("authors") or []):
            name = (name or "").strip()
            if name and name not in NOT_A_PERSON and name not in out:
                out.append(name)
    return out


# A CREDIT MADE ONLY OF SEPARATORS NAMES NOBODY. bwingest writes `" / ".join(authors)`, and a shop
# row whose authors list is `["", ""]` comes out as `" / "`, which is not empty and is not a name.
# Five works were in that state and every count of "credited to nobody" walked past them, because
# the test everywhere was `.strip()`.
NOTHING_BUT_SEPARATORS = re.compile(r"^[\s/／、,・]*$")


def credited(credit):
    """Whether a credit line names anybody at all."""
    return not NOTHING_BUT_SEPARATORS.match(credit or "")


def outstanding(items, credit, ident, claimed):
    """What this pass must answer for: what the corpus credits to nobody, plus what it already did.

    THE SECOND RUN ERASED THE FIRST. The corpus reads this pass's own output, so on the next run
    every work it settled is credited to somebody, drops out of "credited to nobody", and is
    rewritten out of the file, which unsettles it again. The output oscillates and each half of
    the cycle reports a clean run. bwingest.py met the same shape from the other side and subtracts
    its own previous output; here the fix is to keep asking about what it already answered, which
    also means a page that changes its byline is followed rather than frozen.
    """
    return [i for i in items
            if not credited(credit(i)) or ident(i) in claimed]


def groups_among(names):
    """Which of these credits name a body rather than a person, so a reading pass can leave them."""
    return [n for n in names if A_GROUP.search(n or "")]


def credit_line(pairs):
    """The credit as one string, the way every other source in data/source writes one.

    Roles are dropped rather than kept, because the field they are going into is a list of people
    and `原作：` in it would be read as part of a name by everything downstream. What the role is
    worth is the ORDER, which is preserved: the platform lists the writer before the artist.
    """
    seen, out = set(), []
    for name, _role in pairs:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return " / ".join(out)


def main(argv=None):
    """Read the work page of everything the corpus credits to nobody, and write what it says."""
    import argparse
    import datetime
    import json as _json
    import pathlib
    import sys
    import time
    import urllib.request

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--cache", default=None, help="where fetched pages live; outside the repo")
    ap.add_argument("--out", default="data/source/webpages/bylines.yaml")
    ap.add_argument("--reviewed", default="data/queue/bylines-reviewed.yaml",
                    help="bylines read by a person where no shape reaches the host")
    ap.add_argument("--shelf", default="data/queue/admitted.yaml",
                    help="the retailer shelf capture, for print works with no work page")
    ap.add_argument("--shop", default="cmoa.jp",
                    help="which shop's credit to read; NOT bookwalker.jp, see the docstring")
    ap.add_argument("--offline", action="store_true", help="read the cache and make no request")
    a = ap.parse_args(argv)

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import paths                                                              # noqa: E402
    cache = pathlib.Path(a.cache) if a.cache else paths.cache("byline-cache")
    cache.mkdir(parents=True, exist_ok=True)

    ua = ("Mozilla/5.0 (compatible; yurarium/1.0; +https://yurarium.github.io) "
          "bibliographic metadata collection")

    def fetch(url):
        key = re.sub(r"[^A-Za-z0-9]", "_", url)[-140:] + ".html"
        f = cache / key
        if f.exists():
            return f.read_text()
        if a.offline:
            return ""
        req = urllib.request.Request(url, headers={"User-Agent": ua, **host_headers(url)})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                t = r.read(2_000_000).decode("utf-8", "replace")
        except Exception as e:                                                # noqa: BLE001
            t = f"__ERROR__ {type(e).__name__} {e}"
        f.write_text(t)
        time.sleep(1.5)
        return t

    import yaml                                                              # noqa: E402

    # WHAT THIS PASS ALREADY ANSWERED IS STILL ITS QUESTION. The corpus reads this file, so on the
    # second run every work settled here is credited to somebody and drops out of "credited to
    # nobody", and the pass rewrites the file without them, unsettling them again. The output
    # oscillates and each cycle looks like a clean run. bwingest.py met the same shape from the
    # other direction and subtracts its own previous output for the same reason.
    #
    # So the queue is what the corpus credits to nobody PLUS what this file already claims, and
    # every one of them is re-read from its page. A work another source starts crediting stays
    # here harmlessly, because it is the same byline off the same page.
    mine = yaml.safe_load(pathlib.Path(a.out).read_text()) if pathlib.Path(a.out).exists() else {}
    claimed = {r["work_title"] for r in ((mine or {}).get("works") or [])}
    claimed_ids = {r["work_id"] for r in ((mine or {}).get("print_works") or [])}

    series = _json.loads((pathlib.Path(a.build) / "series.json").read_text())["series"]
    wanted = outstanding([w for w in series if w.get("url")],
                         lambda w: w.get("author"), lambda w: w["work"], claimed)

    rev = yaml.safe_load(pathlib.Path(a.reviewed).read_text()) or {}
    by_hand = {r["work_title"]: r for r in (rev.get("works") or [])}
    # A NAME NOBODY STATES IS AN ANSWER. Held apart from the ones a person settled so that
    # "searched and found nothing" cannot be read as "not looked at yet".
    nothing = {r.get("work_id") or r["work_title"]: r for r in (rev.get("unresolved") or [])}

    rows, unread = [], []
    for w in sorted(wanted, key=lambda x: x["work"]):
        u = series_url(w["url"])
        page = fetch(u)
        pairs = byline(u, page) if page and not page.startswith("__ERROR__") else []
        if pairs:
            rows.append((w["work"], u, credit_line(pairs), ""))
        elif w["work"] in by_hand:
            r = by_hand[w["work"]]
            rows.append((w["work"], r.get("url") or u, r["author"], (r.get("note") or "").strip()))
        else:
            unread.append((w["work"], u, (nothing.get(w["work"], {}).get("note") or "").strip()))

    # ── the print half ───────────────────────────────────────────────────────────────────────
    # These are 単行本 with no work page anywhere: 47 of them, almost all yuri anthologies, and
    # MADB and openBD both file them with an empty creator because the publisher registered no
    # single author. コミックシーモア lists the contributors, one row per work, and that capture is
    # already on disk.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from build import norm_work                                              # noqa: E402
    shelf = (yaml.safe_load(pathlib.Path(a.shelf).read_text()) or {}).get("works") or []
    works = _json.loads((pathlib.Path(a.build) / "works.json").read_text())["works"]
    read_print = {r["work_id"]: r for r in (rev.get("print_works") or [])}
    print_rows, print_unread, groups = [], [], []
    for w in outstanding(sorted(works, key=lambda x: x["title"]["ja"]),
                         lambda x: x.get("creator"), lambda x: x["work_id"], claimed_ids):
        names = shelf_credits(shelf, norm_work, norm_work(w["title"]["ja"]), shop=a.shop)
        if names:
            print_rows.append((w["title"]["ja"], w["work_id"], " / ".join(names), a.shop, ""))
            groups += [(w["title"]["ja"], g) for g in groups_among(names)]
        elif w["work_id"] in read_print:
            r = read_print[w["work_id"]]
            # `source` is what the writer below emits and `url` is what a hand-added row
            # carries, so both are accepted. Reading only one silently emptied the field on
            # every rewrite, and the rewrite is how this file is maintained.
            print_rows.append((w["title"]["ja"], w["work_id"], r["author"],
                               r.get("source") or r.get("url") or "",
                               (r.get("note") or "").strip()))
            groups += [(w["title"]["ja"], g) for g in groups_among(r["author"].split(" / "))]
        else:
            print_unread.append((w["title"]["ja"], w["work_id"],
                                 (nothing.get(w["work_id"], {}).get("note") or "").strip()))

    # A FLOOR, because a host that is down and a shelf of works with no byline arrive in the same
    # shape: every page unreadable, nothing settled, a file written with an empty `works` and a run
    # that reports success. The last good capture would be replaced by that. The measured rate is
    # 48 of 49, so "settled nothing at all while the queue was not empty" is clear of a healthy run
    # by the whole distance and is what a dead host looks like.
    print(f"HEALTH: {len(rows)} of {len(wanted)} web work(s) settled, "
          f"{len(print_rows)} of {len(print_rows) + len(print_unread)} print")
    if wanted and not rows:
        print("Refusing to write: not one of the work pages yielded a byline. That is the hosts "
              "being unreachable or the shapes having all changed at once, rather than every work "
              "losing its author, and the three look identical from here.")
        return 1

    js = lambda v: _json.dumps(v, ensure_ascii=False)                          # noqa: E731
    L = ["# Who each source says drew the work, for works the corpus credited to nobody.",
         "#",
         "# WEB WORKS: the byline printed beside the title on the platform's own work page. Read",
         "# by adapters/bylines.py, which parses only shapes proven against a page from that host.",
         "#",
         "# PRINT WORKS: yuri anthologies, which MADB and openBD both file with an empty creator",
         f"# because the publisher registered no single author. The line-up is {a.shop}'s, and",
         "# deliberately not BOOK☆WALKER's: data/queue/bw-review.yaml holds joins waiting to be",
         "# judged against BOOK☆WALKER's credit, and a record settled from that same shop would",
         "# agree with itself.",
         "#",
         "# Nothing here attests a chapter, a date or a genre label. One fact per work.",
         "source: webpages", "platform: bylines", 'platform_name: ""',
         f"retrieved: {datetime.date.today().isoformat()}",
         "record_type: web_work_credit",
         "identification_mode: known-work",
         "works:"]
    for work, url, credit, note in rows:
        L += [f"  - work_title: {js(work)}", f"    url: {js(url)}", f"    author: {js(credit)}"]
        if note:
            L.append(f"    note: {js(note)}")
    L.append("print_works:")
    for work, wid, credit, where, note in print_rows:
        L += [f"  - work_title: {js(work)}", f"    work_id: {js(wid)}", f"    author: {js(credit)}",
              f"    source: {js(where)}"]
        if note:
            L.append(f"    note: {js(note)}")
    if groups:
        L.append("# A credit naming a body rather than a person. Recorded because it is what the")
        L.append("# shop states, and listed here so no pass settles a reading for it as a pen name.")
        L.append("not_a_person:")
        for work, name in groups:
            L += [f"  - work_title: {js(work)}", f"    credit: {js(name)}"]
    L.append("# Searched and not found. Not a queue: each of these says what was looked at.")
    L.append("unresolved:")
    for work, url, note in unread:
        L += [f"  - work_title: {js(work)}", f"    url: {js(url)}",
              f"    note: {js(note or 'no shape reaches this host and nobody has read the page')}"]
    for work, wid, note in print_unread:
        L += [f"  - work_title: {js(work)}", f"    work_id: {js(wid)}",
              f"    note: {js(note or a.shop + ' lists no contributor for this work either')}"]
    pathlib.Path(a.out).write_text("\n".join(L) + "\n")
    read_by_shape = sum(1 for r in rows if not r[3])
    print(f"web: {len(wanted)} credited to nobody; {len(rows)} settled "
          f"({read_by_shape} by a shape, {len(rows) - read_by_shape} read by hand), "
          f"{len(unread)} unresolved")
    print(f"print: {len(print_rows) + len(print_unread)} credited to nobody; "
          f"{len(print_rows)} settled from {a.shop}, {len(print_unread)} unresolved; "
          f"{len(groups)} credit(s) name a body rather than a person")
    for work, url, _note in unread:
        print(f"  UNRESOLVED {work[:38]:40} {url}")
    for work, wid, _note in print_unread:
        print(f"  UNRESOLVED {work[:38]:40} {wid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
