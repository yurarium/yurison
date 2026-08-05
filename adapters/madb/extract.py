#!/usr/bin/env python3
"""Extract 百合姫-imprint works from MADB bulk datasets into source-layer records.

Reads a pinned MADB release from a local cache, selects 単行本 by imprint, resolves them to
単行本シリーズ, and writes one YAML file per work under data/source/madb/.

Deterministic: same release tag in, same records out. No judgment, no network, no model calls.
Classification beyond the mechanical marketing_label is not done here — see docs/REQUIREMENTS.md §6.

Usage:  extract.py --cache $YURI_CACHE/madb-cache/1.2.18 --tag 1.2.18 --out data/source/madb
"""
import argparse, hashlib, json, pathlib, re, sys, unicodedata
from collections import Counter, defaultdict

# Imprint patterns identifying the 一迅社 百合姫 line. Matched against a normalised schema:brand.
# MADB spells this at least seven ways; see docs/MADB.md.
IMPRINTS = ("yurihimecomics", "コミック百合姫", "百合姫コミックス", "百合姫books")

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


def norm(t):
    return re.sub(r"[\s\-.=、。･・]", "", unicodedata.normalize("NFKC", t).lower())


def split_reading(t):
    """Publisher strings embed a reading: '一迅社　∥　イチジンシャ'. Return the name half."""
    return t.split("∥")[0].strip() if "∥" in t else t.strip()


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
                 "Published under 一迅社's 百合姫コミックス imprint (schema:brand). Imprint is\n"
                 "    publisher-side labelling under DEFINITIONS §4.")


def title_index(series):
    """`{normalised series title: series id}`, for volumes MADB has not linked to their series."""
    out = {}
    for sid, s in series.items():
        out.setdefault(norm(primary(s.get("schema:name", ""))), sid)
    return out


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
    if t in titles:
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
        f"  ja: {yaml_str(primary(s.get('schema:name', '')))}",
    ]
    if reading(s.get("schema:name", "")):
        L.append(f"  yomi: {yaml_str(reading(s.get('schema:name', '')))}")
    L += [
        f"creator: {yaml_str(flat(s.get('schema:creator', '')))}",
        f"publisher: {yaml_str(split_reading(primary(s.get('schema:publisher', ''))))}",
        f"imprint: {yaml_str(split_reading(primary(s.get('schema:brand', ''))))}",
        f"volume_count: {len(vs)}",
    ]
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

    pats = [norm(p) for p in IMPRINTS]
    vols = [r for r in books if any(p in norm(flat(r.get("schema:brand", ""))) for p in pats)]

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


if __name__ == "__main__":
    main()
