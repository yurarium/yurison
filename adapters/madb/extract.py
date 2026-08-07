#!/usr/bin/env python3
"""Extract 百合姫-imprint works from MADB bulk datasets into source-layer records.

Reads a pinned MADB release from a local cache, selects 単行本 by imprint, resolves them to
単行本シリーズ, and writes one YAML file per work under data/source/madb/.

Deterministic: same release tag in, same records out. No judgment, no network, no model calls.
Classification beyond the mechanical marketing_label is not done here — see docs/REQUIREMENTS.md §6.

Usage:  extract.py --cache $YURI_CACHE/madb-cache/1.2.18 --tag 1.2.18 --out data/source/madb
"""
import argparse, hashlib, json, pathlib, re, sys, unicodedata
from collections import Counter, defaultdict, namedtuple

# Imprint patterns identifying the 一迅社 百合姫 line. Matched against a normalised schema:brand.
# MADB spells this at least seven ways; see docs/MADB.md.
IMPRINTS = ("yurihimecomics", "コミック百合姫", "百合姫コミックス", "百合姫books")

# The role MADB writes in a bracket around a publisher's name, and what each one means. A value is
# read as a role ONLY if it is in here. MADB brackets other things in the same position: `[LEGO]`,
# `[Shueisha]` and `[ヒゲの筆]` are names, and a rule stripping every bracket leaves those credits
# naming nobody. 発売 and 頒布 are the two that matter in this corpus and the rest are here because
# they occur in the release and would otherwise be read as part of a name.
PUBLISHER_ROLES = {
    "発売": "distributor",
    "頒布": "distributor",
    "発売所": "distributor",
    "共同刊行・発売": "co-publisher",
    "共同刊行": "co-publisher",
    "発行": "publisher",
    "発行元": "publisher",
    "発行所": "publisher",
    "製作": "producer",
    "制作": "producer",
    "印刷": "printer",
    "出版者不明": "unknown",
}

ROLE_HEAD = re.compile(r"^\s*[\[［]\s*([^\]］]*?)\s*[\]］]\s*")
ROLE_TAIL = re.compile(r"\s*[（(]\s*([^）)]*?)\s*[）)]\s*$")

# One publisher credit: the name, the role it holds, and MADB's own word for that role.
Party = namedtuple("Party", "name role stated")

# Health assertions — the adapter refuses to write if the source stops looking like itself (§6).
MIN_VOLUMES = 400
MIN_WORKS = 150


def flat(v):
    """MADB fields are variously str, dict or list. Collapse to a display string."""
    if isinstance(v, list):
        return " / ".join(flat(x) for x in v)
    if isinstance(v, dict):
        return str(v.get("@value", v.get("@id", "")))
    return "" if v is None else str(v)


def reading(v):
    """Pull the ja-hrkt reading MADB attaches alongside a name, if present."""
    if isinstance(v, list):
        for x in v:
            if isinstance(x, dict) and x.get("@language") == "ja-hrkt":
                return str(x.get("@value", ""))
    return ""


def primary(v):
    """The non-reading half of a name field."""
    if isinstance(v, list):
        for x in v:
            if isinstance(x, str):
                return x
    return flat(v)


def values(v):
    """Every name a MADB field states, without the readings written after them.

    WHY `primary` IS NOT ENOUGH, and it is the same fault in two fields. MADB gives one logical
    field as a bare string or as a list holding the names first and their ja-hrkt readings after.
    `primary` takes the first string, which is right for a title and wrong for a field whose values
    are a set. `schema:brand` is ["IDコミックス", "Yurihime comics", …] and the first value is the
    umbrella line every 一迅社 comic carries; `schema:publisher` is ["[発売]講談社", "一迅社"] and
    the first value is the distributor. Both faults are one value being read where MADB stated
    several.
    """
    if isinstance(v, list):
        return [x.strip() for x in v if isinstance(x, str) and x.strip()]
    return [v.strip()] if isinstance(v, str) and v.strip() else []


def norm(t):
    return re.sub(r"[\s\-.=、。･・]", "", unicodedata.normalize("NFKC", t).lower())


def split_reading(t):
    """Publisher strings embed a reading: '一迅社　∥　イチジンシャ'. Return the name half."""
    return t.split("∥")[0].strip() if "∥" in t else t.strip()


def as_stated(v):
    """A field as MADB states it: every value, its cataloguing intact, the readings off.

    This is the raw kept beside the interpretation. REQUIREMENTS §5 draws the line at what the
    source said, so `[発売]講談社 / 一迅社` stays on the record next to the publisher read out of
    it, and a reader who disagrees with the reading can see what it was made from.
    """
    got = [split_reading(x) for x in values(v)]
    return " / ".join(got) if got else split_reading(primary(v))


def party(text):
    """One publisher credit as its name, the role it holds, and MADB's word for that role.

    MADB writes the role in a bracket before the name, `[発売]講談社`, and sometimes after it,
    `小学館クリエイティブ (発売)`. Both are cataloguing rather than part of the name. Anything the
    bracket holds that PUBLISHER_ROLES does not name is left where it is, because MADB brackets
    names in the same position and stripping `[ヒゲの筆]` leaves a credit naming nobody.

    A party with no role stated is the publisher. That is what MADB means by writing a name plain
    beside one it has marked.
    """
    name, role, stated = split_reading(text), "publisher", ""
    head = ROLE_HEAD.match(name)
    if head and head.group(1) in PUBLISHER_ROLES:
        role, stated, name = PUBLISHER_ROLES[head.group(1)], head.group(1), name[head.end():].strip()
    tail = ROLE_TAIL.search(name)
    if tail and tail.group(1) in PUBLISHER_ROLES:
        if not stated:
            role, stated = PUBLISHER_ROLES[tail.group(1)], tail.group(1)
        name = name[:tail.start()].strip()
    return Party(name, role, stated)


def publishers(rec):
    """Every party MADB names on a record, in the order it names them."""
    return [party(x) for x in values(rec.get("schema:publisher", ""))]


def publisher_of(rec):
    """The party that PUBLISHED, which is not the party MADB names first.

    MADB lists a distributor ahead of the publisher: ["[発売]講談社", "一迅社"] is 一迅社's book put
    into shops by 講談社. Reading the first value stored 講談社 as the publisher of 132 works whose
    publisher is 一迅社, and a per-publisher count of 一迅社 came out roughly five times short
    because of it.

    Where nobody holds the publisher role the answer is nobody. A distributor is not promoted into
    the empty seat, and `publishers` still names who MADB did state.
    """
    for p in publishers(rec):
        if p.role == "publisher":
            return p
    return Party("", "", "")


# The 百合姫 spellings in the form they are compared in. Built once so that the selection in
# `main`, the per-work label in `by_isbn.label_for` and the imprint stored on a record all ask the
# same question; three copies of the spelling list would answer differently the day MADB adds an
# eighth spelling (STANDING-INSTRUCTIONS §3).
IMPRINT_PATTERNS = tuple(norm(p) for p in IMPRINTS)


def is_yuri_imprint(text):
    """Whether a brand names 一迅社's 百合姫 line."""
    n = norm(text)
    return any(p in n for p in IMPRINT_PATTERNS)


def imprint_of(recs):
    """`(the imprint to store, the record it was read from)`, over a record and its volumes.

    THE BRAND THAT EARNED THE LABEL IS THE ONE THE RECORD SHOULD STATE. `main` selects VOLUMES
    whose brand is a 百合姫 line and writes the SERIES record. MADB states that series brand as
    ["IDコミックス", "Yurihime comics", …], so reading the first value stored 117 works as
    `imprint: IDコミックス` beside `marketing_label: yuri`. IDコミックス is 一迅社's general comics
    line and makes no yuri claim at all, so the work page had a label whose evidence the record did
    not hold, and `adapters/classify/credence.py` withheld the row instead of quoting a term that
    would have misled a reader.

    WHY NOT SIMPLY THE LAST VALUE, which is the more specific one in all 47,687 records stating
    more than one brand. Because it is not always a brand: MADB writes ["Emerald comics", "Romance
    comics = ロマンスコミックス", "プロポーズのゆくえ"] and the last value there is a title. So the
    matched brand wins where the pass matched one, and every other record keeps the value it
    already had.

    `recs` is the record itself followed by its volumes. The series brand carries the match on 299
    of the 302 works; the other three are where selection on the volumes is the only evidence
    there is, and MADB leaves the brand off the series record entirely on one of them.
    """
    for rec in recs:
        for b in (split_reading(x) for x in values(rec.get("schema:brand", ""))):
            if is_yuri_imprint(b):
                return b, rec
    for rec in recs:
        got = values(rec.get("schema:brand", ""))
        if got:
            return split_reading(got[0]), rec
    return split_reading(primary(recs[0].get("schema:brand", ""))), recs[0]


def local_id(v):
    return flat(v).rsplit("/", 1)[-1]


def yaml_str(t):
    """Quote defensively; these are Japanese strings that may contain YAML metacharacters."""
    return '"' + str(t).replace("\\", "\\\\").replace('"', '\\"') + '"'


def load(cache, name):
    p = pathlib.Path(cache) / name
    if not p.exists():
        sys.exit(f"missing {p} — download the release assets first")
    return json.loads(p.read_text())["@graph"]


# Which pass wrote a record. Each pass deletes only its own, because a pass must not delete what
# it is not looking at: the ISBN route writes into this same directory and a blanket wipe here
# removed everything it had just produced.
ROUTE_IMPRINT = "imprint-selection"

# The label a record carries, and the sentence saying why. Selection by imprint IS the evidence,
# so this route states it; a route that selected on something else must state something else,
# because DEFINITIONS §4 takes only publisher-side labelling and a shop's shelf is not that.
LABEL_IMPRINT = ("yuri",
                 "Published under a 一迅社 百合姫 imprint. The `imprint` field names the brand\n"
                 "    that was matched, spelled as MADB spells it (schema:brand). Imprint is\n"
                 "    publisher-side labelling under DEFINITIONS §4.")


PARALLEL_TITLE = re.compile(r"^(?P<ja>.+?)\s*=\s*(?P<en>[^=]+)$")
JAPANESE_TEXT = re.compile(r"[぀-ヿ㐀-鿿]")


def title_proper(name):
    """The title without the parallel title ISBD records after ` = `.

    WHAT ` = ` MEANS. It introduces a 並列タイトル, the same title in another language, transcribed
    from the book's own title page. `リリィシステム = LILY SYSTEM` is one work with one title and an
    English name beside it, and storing the whole string made the cataloguing punctuation part of
    the name. A reader saw it, a search had to match it, and two records of one work compared
    unequal: several pairs were merged by hand after shipping as duplicates for exactly this.

    THE ENGLISH HALF IS NOT DISCARDED. `parallel_title` returns it, and it is the publisher's own
    English name, which is worth more than any romanisation we could derive.

    ONLY A LATIN PARALLEL TITLE IS SPLIT. `A = B` where B holds Japanese is not a translation, and
    8 records have that shape, so the whole string stays as written.
    """
    s = str(name or "").strip()
    m = PARALLEL_TITLE.match(s)
    # More than one ` = ` is not a title beside its translation, and guessing which half is the
    # name would be inventing one. `X = Y = Z` stays whole.
    if not m or s.count("=") != 1 or JAPANESE_TEXT.search(m.group("en")):
        return s
    return m.group("ja").strip()


def parallel_title(name):
    """The English name a title carries after ` = `, or '' where it carries none."""
    s = str(name or "").strip()
    m = PARALLEL_TITLE.match(s)
    if not m or s.count("=") != 1 or JAPANESE_TEXT.search(m.group("en")):
        return ""
    return m.group("en").strip()


def title_index(series):
    """`{normalised series title: series id}`, for volumes MADB has not linked to their series."""
    out = {}
    for sid, s in series.items():
        out.setdefault(norm(primary(s.get("schema:name", ""))), sid)
    return out


def publisher_names(rec):
    """Every party MADB names, normalised, for comparing one record against another.

    A SET AND NOT ONE VALUE. MADB names the distributor beside the publisher on one record and the
    publisher alone on the other: ハイガクラ's volumes state ["[頒布]講談社", "一迅社"] and its
    series record states 一迅社. Comparing a single value against a single value refused 14 title
    joins of that shape across release 1.2.18, ハイガクラ and Landreaall and 顔に泥を塗る among
    them, all of which are one work under one publisher.

    The role is off the name but is not itself compared, because who put a volume into shops says
    nothing about whether two records describe one work. `[Shueisha]` keeps its bracket, which is
    what `party` decided and which lets 少年ジャンプ+赤 match itself.
    """
    return {norm(p.name) for p in publishers(rec) if norm(p.name)}


def strip_role(part):
    """One credit with the role marker off it.

    MADB writes `[著]`, doubles the delimiter as `[[著]]`, and puts the role in a bracket of its
    own after the name in `[上田香子][訳]`. Split out of `people` so that a reader wanting a
    different rule about WHICH credits count still shares the rule about what a role looks like:
    `madb/by_title.py` is that reader (STANDING-INSTRUCTIONS §3).
    """
    name = re.sub(r"\[+", "[", re.sub(r"\]+", "]", part))
    return re.sub(r"\[[著作画原訳編監修構成脚本案翻・\s]*\]", "", name).strip()


def people(rec):
    """The creators named on a record, without their roles, and without a bare reading."""
    out = set()
    for part in re.split(r"\s*/\s*", flat(rec.get("schema:creator", ""))):
        name = strip_role(part)
        # A trailing all-katakana part is the reading of the name before it, not a second person.
        if name and not re.fullmatch(r"[\u30a0-\u30ff・\s]+", name):
            out.add(norm(name))
    return out


def agrees(vol, ser):
    """Whether anything BUT the title says this volume belongs to this series.

    WHY A TITLE IS NOT ENOUGH. `トワ・エ・モア` is a コンパス anthology from 1996 with no creator
    named, and it is also a 講談社 KCデラックス series by 仲藤ぬい from 2024. Matching on the
    normalised title alone filed the second inside the first, so one work held volumes 28 years and
    two publishers apart, and the reader saw an unnumbered 1996 volume sitting above 第1巻 2024.

    Publisher agreement is deliberately loose about the house changing hands: 一迅社's yuri line
    passed to 講談社 and those volumes disagree about the publisher while plainly being one work.
    That case is carried by the creator, which does agree, so requiring ANY of the three to agree
    keeps it while dropping the collision above. Measured over the whole corpus this refuses two
    volume joins, both of them トワ・エ・モア.

    The publisher test compares the SET of parties MADB names rather than one value, which is
    `publisher_names` and its reasoning. It made 14 more title joins across release 1.2.18 and
    refused none that had been made, so the refusal count fell from 1,195 to 1,181 and no work in
    the imprint pass was regrouped.

    A FOURTH TEST WAS PROPOSED AND IS REFUTED, recorded here so it is not proposed again. Where an
    anthology names nobody, the argument runs, none of the three fields can speak and an exactly
    agreeing publication month is what is left. Three measurements over release 1.2.18 say
    otherwise.

    It joins nothing. Of the 1,195 title matches this function refuses across all 401,311 book
    records, 89 name no creator on either side and not one of those 89 has an agreeing month,
    because MADB leaves 607 of the 1,195 series records undated. The 25 joins it appeared to settle
    were measured in the works list, where a print-only row carries its own `first_publication`
    date twice, once as the row's `first` and once inside its `print` block. Comparing those two is
    comparing a number with itself, and all 54 pairs it agreed on were rows already joined to the
    work they were being matched against. No new join exists for it to make.

    It would break the class it was drawn from. A tie-in anthology is raced out by rival houses in
    the month the game ships: ペルソナ4コミックアンソロジー is two different books in 2009-01, one
    光文社 and one 一迅社, and To heart 2アンソロジーコミック is three in 2005-07 under three
    publishers. 17 creatorless title-and-month groups in the release name more than one publisher.

    And the 一迅社 case it was drawn for is already carried. citrus is catalogued as 一迅社 and as
    [発売]講談社 with no creator on either record, and the imprint is IDコミックス on both, so the
    third test joins it. The premise that nothing but the date is left is what was wrong.
    """
    if people(vol) & people(ser):
        return True
    if publisher_names(vol) & publisher_names(ser):
        return True
    b = norm(split_reading(primary(vol.get("schema:brand", ""))))
    return bool(b) and b == norm(split_reading(primary(ser.get("schema:brand", ""))))


def key_of(r, series, titles):
    """`(work key, how it was reached)` for one volume.

    Roughly a third of volumes carry no schema:isPartOf — recent NDL-sourced records MADB has not
    yet resolved to a series. Dropping them would silently lose 30% of the corpus, so fall back to
    grouping by normalised title, and record which route produced each work.

    ONE PLACE THIS RULE LIVES. by_isbn.py asks the same question of every volume in the dataset in
    order to complete a work a single ISBN identified, and a second copy of the rule there would
    put a volume in a different work depending on which pass was looking at it.
    """
    sid = local_id(r.get("schema:isPartOf", ""))
    if sid in series:
        return sid, "series-link"
    t = norm(primary(r.get("schema:name", "")))
    # A title match needs something else to agree with it. Where nothing does, the volume is its
    # own work rather than somebody else's.
    if t in titles and agrees(r, series[titles[t]]):
        return titles[t], "title-match"
    return "T:" + t, "title-only"


def group(vols, series):
    """`(by_series, grouping)`: volumes gathered into works, and how each work was gathered."""
    titles = title_index(series)
    by_series, grouping = defaultdict(list), {}
    for r in vols:
        key, how = key_of(r, series, titles)
        by_series[key].append(r)
        grouping.setdefault(key, how)
        if grouping[key] == "series-link" and how != "series-link":
            grouping[key] = "mixed"
    return by_series, grouping


def dedupe(by_series):
    """MADB carries duplicate volume records for the same printing (e.g. 私に天使が舞い降りた! vol 15
    as both M1033504 and M1033586). Deduplicate on ISBN, else on volume number + date."""
    for key, vs in by_series.items():
        seen, keep = set(), []
        for r in sorted(vs, key=lambda r: r["schema:identifier"]):
            isbn = flat(r.get("schema:isbn", "")).strip()
            k = isbn or (flat(r.get("schema:volumeNumber", "")),
                         flat(r.get("schema:datePublished", "")))
            if k in seen:
                continue
            seen.add(k)
            keep.append(r)
        by_series[key] = keep
    return by_series


def volume_count(vs):
    """How many VOLUMES a work has, which is not how many records describe them.

    ささやくように恋を唄う holds four of its volumes twice, a standard and a special edition of
    each, differing in the ISBN and in nothing else MADB records. Counting records said the work
    was 16 volumes long while the list of them showed 12, on the same page.

    Editions are one volume where the number AND the date agree. An unnumbered volume counts once
    on its own, because there is nothing to match it against.
    """
    seen, n = set(), 0
    for r in vs:
        num = flat(r.get("schema:volumeNumber", "")).strip()
        key = (num, flat(r.get("schema:datePublished", "")).strip())
        if num and key in seen:
            continue
        seen.add(key)
        n += 1
    return n


def work_id(sid):
    """Synthetic ids must be stable and unique. Stripping non-ASCII would erase a Japanese title
    entirely and collapse every title-only work onto one id, so hash the normalised title."""
    return ("madb-t-" + hashlib.sha1(sid[2:].encode()).hexdigest()[:12]
            if sid.startswith("T:") else sid)


def render(sid, vs, series, how, tag, retrieved, route, label, extra=()):
    """The YAML text of one work record.

    ONE PLACE THE RECORD SHAPE IS DECIDED. Two passes select volumes by different criteria and
    both write into data/source/madb/; a second copy of this layout would drift the moment either
    side gained a field.
    """
    synthetic = sid.startswith("T:")
    # A title-only work has no cm104 record; take its descriptive fields from the first volume.
    s = vs[0] if synthetic else series[sid]
    wid = work_id(sid)
    vs = sorted(vs, key=lambda r: (flat(r.get("schema:datePublished", "")),
                                   flat(r.get("schema:volumeNumber", ""))))
    dates = [flat(r.get("schema:datePublished", "")) for r in vs if r.get("schema:datePublished")]
    value, note = label

    L = [
        "# Source-layer record. Stored as fetched; never hand-edited (REQUIREMENTS §5).",
        "# Curation and content classification belong in the overlay layer.",
        "source: madb",
        f"source_version: {yaml_str(tag)}",
        f"retrieved: {retrieved}",
        f"work_id: {wid}",
        f"route: {route}",
        f"grouping: {how}",
    ]
    if not synthetic:
        L += [f"madb_id: {sid}",
              f"madb_url: https://mediaarts-db.artmuseums.go.jp/id/{sid}"]
    else:
        L += ["# No cm104 series record; volumes grouped by normalised title. Verify before",
              "# treating as one work — see docs/MADB.md.",
              "madb_id: null"]
    L += [
        "record_type: manga_book_series",
        "title:",
        f"  ja: {yaml_str(title_proper(primary(s.get('schema:name', ''))))}",
    ]
    if parallel_title(primary(s.get("schema:name", ""))):
        L.append(f"  en: {yaml_str(parallel_title(primary(s.get('schema:name', ''))))}")
        L.append("  en_basis: parallel-title")
    if reading(s.get("schema:name", "")):
        L.append(f"  yomi: {yaml_str(reading(s.get('schema:name', '')))}")
    # WHO PUBLISHED AND WHO DISTRIBUTED, kept apart, with the field they were read out of kept
    # beside them. A distributor and a publisher hold different roles and a record that states one
    # string for both leaves every consumer to guess which it has (REQUIREMENTS §5).
    #
    # A THIN SERIES RECORD DOES NOT SILENCE ITS VOLUMES. MADB leaves schema:publisher off 10 of
    # these series records while every volume of them names 一迅社, and after the imprint was fixed
    # those were the only works whose label still had nothing quotable: a term and nobody to
    # attribute it to. Where the summary says nothing, the books it collects do, and the record
    # names which of the two it read.
    chain = [s] + list(vs)
    pubrec = next((r for r in chain if values(r.get("schema:publisher", ""))), s)
    parties = publishers(pubrec)
    who = publisher_of(pubrec)
    pub_stated = as_stated(pubrec.get("schema:publisher", ""))
    # The imprint that carries this record's label, or the brand as stated where nothing matched.
    imprint, imprec = imprint_of(chain)
    imp_stated = as_stated(imprec.get("schema:brand", ""))
    L += [
        f"creator: {yaml_str(flat(s.get('schema:creator', '')))}",
        f"publisher: {yaml_str(who.name)}",
    ]
    # The raw is written wherever reading it changed the answer, and left out where it would only
    # repeat the line above. Correcting how a source is READ is right; editing what it SAID is not.
    if pub_stated != who.name:
        L.append(f"publisher_stated: {yaml_str(pub_stated)}")
    if pubrec is not s:
        L.append("publisher_from: volumes")
    if len(parties) > 1 or any(p.stated for p in parties):
        L.append("publishers:")
        for p in parties:
            L.append(f"  - name: {yaml_str(p.name)}")
            L.append(f"    role: {p.role}")
            if p.stated:
                L.append(f"    role_stated: {yaml_str(p.stated)}")
    L.append(f"imprint: {yaml_str(imprint)}")
    if imp_stated != imprint:
        L.append(f"imprint_stated: {yaml_str(imp_stated)}")
    if imprec is not s:
        L.append("imprint_from: volumes")
    L.append(f"volume_count: {volume_count(vs)}")
    if dates:
        L.append(f"first_published: {dates[0]}")
        L.append(f"last_published: {dates[-1]}")
    L.append("volumes:")
    for r in vs:
        L.append(f"  - madb_id: {r['schema:identifier']}")
        if r.get("schema:volumeNumber"):
            L.append(f"    number: {yaml_str(flat(r['schema:volumeNumber']))}")
        if r.get("schema:isbn"):
            L.append(f"    isbn: {yaml_str(flat(r['schema:isbn']))}")
        if r.get("schema:datePublished"):
            L.append(f"    published: {flat(r['schema:datePublished'])}")
    # What admitted the work, where that is not one of the axes below. §2's third branch is a
    # comparator listing it, and a reader is owed the name of the comparator.
    L += list(extra)
    # Mechanical, publisher-side. The interpretive axis is deliberately absent (DEFINITIONS §3).
    L += [
        f"marketing_label: {value}",
        "marketing_label_basis:",
        "  source: madb",
        f"  url: {'' if synthetic else f'https://mediaarts-db.artmuseums.go.jp/id/{sid}'}",
        f"  retrieved: {retrieved}",
        "  note: >-",
        f"    {note}",
        "",
    ]
    return "\n".join(L)


def rated_count(by_series):
    """Volumes carrying any adult marking. Flagged for review, never auto-included (§7)."""
    return sum(1 for vs in by_series.values()
               if any(flat(r.get("schema:contentRating", "")).strip() for r in vs))


def write(out, by_series, grouping, series, tag, retrieved, route, label):
    """Write one record per work, clearing what THIS route wrote last time and nothing else."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.yaml"):
        text = f.read_text()
        # A record with no route line predates the field and belongs to the imprint pass, which is
        # the only writer that existed then.
        if f"route: {route}" in text or (route == ROUTE_IMPRINT and "\nroute: " not in text):
            f.unlink()
    for sid, vs in sorted(by_series.items()):
        (out / f"{work_id(sid)}.yaml").write_text(
            render(sid, vs, series, grouping[sid], tag, retrieved, route, label))
    return len(by_series)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--tag", required=True, help="MADB release tag, recorded in every record")
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True, help="ISO date the cache was downloaded")
    a = ap.parse_args()

    books = load(a.cache, "metadata101.json")
    series = {r["schema:identifier"]: r for r in load(a.cache, "metadata104.json")}

    vols = [r for r in books if is_yuri_imprint(flat(r.get("schema:brand", "")))]

    if len(vols) < MIN_VOLUMES:
        sys.exit(f"HEALTH: {len(vols)} volumes < {MIN_VOLUMES}; imprint spelling may have changed. "
                 "Refusing to write (see docs/REQUIREMENTS.md §6).")

    by_series, grouping = group(vols, series)
    by_series = dedupe(by_series)

    if len(by_series) < MIN_WORKS:
        sys.exit(f"HEALTH: {len(by_series)} works < {MIN_WORKS}. Refusing to write.")

    rated = rated_count(by_series)
    kept = sum(len(v) for v in by_series.values())
    write(a.out, by_series, grouping, series, a.tag, a.retrieved, ROUTE_IMPRINT, LABEL_IMPRINT)

    counts = Counter(grouping.values())
    print(f"volumes matched : {len(vols)}  ({len(vols)-kept} duplicates dropped)")
    print(f"works written   : {len(by_series)}  -> {a.out}")
    for how in ("series-link", "mixed", "title-match", "title-only"):
        if counts[how]:
            print(f"  {how:12}: {counts[how]}")
    print(f"content-rated   : {rated} (review before inclusion — DEFINITIONS §7)")

    # WHAT THE RECORDS NOW STATE, reported rather than assumed. Both numbers below were the two
    # faults: an imprint quoting the umbrella line, and a distributor standing where the publisher
    # belongs. A pass that stops resolving either should say so on the run it stops.
    quoting = distributed = unnamed = 0
    for sid, vs in by_series.items():
        s = vs[0] if sid.startswith("T:") else series[sid]
        chain = [s] + list(vs)
        if is_yuri_imprint(imprint_of(chain)[0]):
            quoting += 1
        pubrec = next((r for r in chain if values(r.get("schema:publisher", ""))), s)
        if any(p.role == "distributor" for p in publishers(pubrec)):
            distributed += 1
        if not publisher_of(pubrec).name:
            unnamed += 1
    print(f"imprint quotable: {quoting} of {len(by_series)} works state the 百合姫 brand that "
          "carries their label")
    print(f"distributors    : {distributed} works name one beside the publisher")
    print(f"no publisher    : {unnamed} works where MADB names nobody in that role")


if __name__ == "__main__":
    main()
