# Name-record faults: causes, not corrections

Diagnosis of the five defects raised against `data/names/titles.yaml` by
[reading-review.md](reading-review.md). That document proposed corrected VALUES. This one asks
which pass wrote each wrong value, why, and how many other records sit behind the same cause.

Nothing was edited. `build.py`, `deploy.sh` and git were not run. Every claim below was reproduced
offline from the stored responses in `../names-cache` (695 files) and from the checked-in YAML, by
calling the pass functions directly.

## Where the five stand today

Three of the five have already had their `reading` field corrected by `data/names/curated.yaml`
(reviewed 2026-08-04, after the review was written). The code that produced them has not changed,
so all five causes are live.

| # | fault | live in `reading`? | cause is in |
|---|---|---|---|
| 1 | お姉さまと巨人: subtitle missing | **yes** | pass 2, MangaUpdates |
| 2 | 彩香ちゃん: another work's reading | no, curated over; survives in `reading_conflicts` | pass 2, Wikidata |
| 3 | スケバンと転校生: reading longer than the name | no, curated over; survives in `reading_conflicts` | pass 2, MangaUpdates |
| 4 | 〇〇 read as レイキゴウ | no, curated over; survives in `reading_conflicts` and in stale `furigana_spans` | pass 4, Sudachi |
| 5 | を back-converted to ウォ | **yes**, 5 records | `kana._REVERSE` |

Faults 1 and 3 are one cause. Fault 2 is a second cause in the same pass. So the five defects are
four bugs, and two of them are in pass 2's matching rather than in any reading logic.

---

## 1 and 3. MangaUpdates: the title matched is not the title romanised

### What is stored

`お姉さまと巨人 ～お嬢さまが異世界転生～` holds

```
reading: オネエ サマ ト キョジン
reading_basis: back-converted
reading_source: mangaupdates
reading_url: https://www.mangaupdates.com/series/otyofae/onee-sama-to-kyojin
```

Nine morae for a title whose surface cannot be read in fewer than seventeen. This is the length
outlier the review found, and it is still the live value: the curated entry for this title
(curated.yaml:8084) supplies an `en` and no reading.

`スケバンと転校生` held, before curation, `スケバン ト テンコウセイ ガ クダラナイ アソビ オ スル ダケ ノ
ハナシ`, twenty-nine morae against a surface that tops out at nineteen. It now carries the
researched `スケバン ト テンコウセイ`, with the long value demoted to `reading_conflicts`.

### The line responsible

`adapters/names/pass2_bulk.py`, `MangaUpdates.lookup`, line 495:

```python
if norm(hit.get("hit_title")) != norm(ja):
    continue
rec = hit.get("record") or {}
return {ja: self._facts(ja, rec, cache)}
```

and then `_facts`, line 521:

```python
romaji = rec.get("title")
```

`hit_title` is the string MangaUpdates matched, which may be any of the record's associated titles.
`record.title` is the record's own primary title. They are two different titles of the same series,
and the identity check is applied to the first while the romanisation is taken from the second.

Replayed from the cache, both cases are exact:

| our key | `hit_title` | `record.title` |
|---|---|---|
| お姉さまと巨人 ～お嬢さまが異世界転生～ | お姉さまと巨人 ～お嬢さまが異世界転生～ | Onee-sama to Kyojin |
| スケバンと転校生 | スケバンと転校生 | Sukeban to Tenkousei ga Kudaranai Asobi o Suru dake no Hanashi |

(`names-cache/mu-search-81d0c4ca9e5a17161fcde1f4.json` and
`names-cache/mu-search-fc2268600b772baf9785f444.json`.)

The module docstring names this risk and then guards the wrong half of it. Line 67: "MangaUpdates
by requiring `hit_title` to equal the query." That establishes the record is the right RECORD. It
does not establish that `record.title` is a romanisation of the string we asked about, and on a
series catalogued under more than one Japanese title it usually is not.

The only downstream check is `norm(romaji) != norm(ja)` at line 523, which compares a Latin string
to a Japanese one and therefore always passes. `looks_romanised` then returns True, because the
string genuinely is a romanisation, just of a different title. Nothing in the path can notice.

### How many others

Replaying every cached MangaUpdates search against the 1,086 keys in `titles.yaml`: 424 titles have
a cached search, and 34 of them produce a back-converted reading fact. Testing each against a mora
band derived from the surface (kana count plus one mora per kanji at the low end, plus four at the
high end, with slack for Latin and digits) flags exactly two:

```
OUT-OF-BAND [17,46] got  9  お姉さまと巨人 ～お嬢さまが異世界転生～ | Onee-sama to Kyojin
OUT-OF-BAND  [8,19] got 29  スケバンと転校生               | Sukeban to Tenkousei ga Kudaranai Asobi o Suru dake no Hanashi
```

No false positives among the other 32. So the class has two members in the current data, and both
are the reported ones. The exposure is larger than the hit count: 30 titles hold a live
MangaUpdates back-converted reading and 84 authors hold one, and every one of them was accepted
without any check that the reading fits the name.

The same faulty match also fed the English side. Both records carry the wrong romaji in
`en_conflicts` (`Onee-sama to Kyojin`; `Sukeban to Tenkousei ga Kudaranai Asobi o Suru dake no
Hanashi`), so this is not only a reading fault.

### Fix

Two parts, and the second is the one that generalises.

1. In `_facts`, do not treat `record.title` as the romanisation of `ja` unless the match was on the
   record's own title. MangaUpdates does not return the record's Japanese title in the search
   result, but `_detail` already fetches the series record for every hit and its `associated` list
   carries the alternative titles. Where `hit_title` appears in `associated` and is not the
   record's title-of-record, the romanisation belongs to a different string and should be dropped,
   or at most recorded as a candidate.

2. Add a coverage check to every back-converted reading before it is recorded, in `kana` or in
   `store.record`: the reading's mora count must fall inside the band the surface allows. The band
   above separated the two faults from 32 correct readings with no misses in either direction, and
   it is cheap. This catches the same fault from any source, including AniList when it returns,
   which has the identical shape at line 438.

A stricter surface-anchor test (every kana run of the title must appear in order in the reading)
was tried and rejected: it flags fifteen of the 34, because it cannot see through は/ワ, を/オ,
づ/ズ and ー. The mora band needs no such table.

---

## 2. Wikidata: an alias match given the item's own label

### What is stored

`彩香ちゃんは弘子先輩を落としたい` held `アヤカ チャン ワ ヒロコ センパイ ニ コイシテル`, which is the
reading of `彩香ちゃんは弘子先輩に恋してる`. Both keys exist in `titles.yaml`. Curation has since
replaced the reading with `アヤカチャン ワ ヒロコ センパイ ヲ オトシタイ`; the wrong value survives as

```
reading_conflicts:
- basis: back-converted
  source: wikidata
  value: アヤカ チャン ワ ヒロコ センパイ ニ コイシテル
```

and its twin survives in `en_conflicts` as the romaji `Ayaka-chan wa Hiroko-senpai ni Koishiteru`.

### The line responsible

`TITLE_SPARQL`, pass2_bulk.py:213:

```sparql
SELECT ?item ?ja ?en ?type WHERE {
  VALUES ?ja { %s }
  ?item rdfs:label|skos:altLabel ?ja .
  ...
```

`skos:altLabel` means the query matches ALIASES as well as labels, and `?en` is the item's English
label whatever matched. `_title_fact` (line 325) never looks at which of the two it was, and
cannot: unlike `AUTHOR_SPARQL` at line 202, `TITLE_SPARQL` does not select `?jalabel`, so the
information is not in the response.

The author path has exactly this guard, twelve lines earlier, with the same failure written out in
its comment: 古川楊也 is an alias of the person whose P1814 reads ホシノ カツラ, so taking the item's
kana for an alias match publishes a reading of a different name. Line 292:

```python
own = [b for b in group if (b.get("jalabel") or {}).get("value") == ja]
if not own:
    return None
```

The title path has no equivalent. The bug is the author bug, unfixed on the other side of the same
class.

Replaying the cached SPARQL responses confirms it precisely. Q115118144 is bound by two of our
keys, and both receive the same English label:

```
彩香ちゃんは弘子先輩に恋してる  | Ayaka-chan wa Hiroko-senpai ni Koishiteru   (the item's own label)
彩香ちゃんは弘子先輩を落としたい | Ayaka-chan wa Hiroko-senpai ni Koishiteru   (an alias)
```

This fault is invisible to any length or shape check. The two titles are 14 and 15 morae, both
inside the band that catches faults 1 and 3, and the reading is a perfectly formed reading of a
real title. Only the label/alias distinction separates them, which is why the review called it the
worst class here.

### How many others

Wikidata answered on 210 of our titles and produced 177 facts: 51 believed romanisations, 126
candidates, 24 back-converted readings. Twenty of those readings are live in `titles.yaml`.

Exactly one alias collision is provable from the cache, the one reported. That is a lower bound,
not a count. It is provable only because we happen to hold BOTH titles, so two of our keys bind the
same item. Where we hold only the alias, there is nothing in the stored response to compare against,
because `?jalabel` was never requested. Every one of the 177 facts is potentially in that position.

**What would settle it:** add `OPTIONAL { ?item rdfs:label ?jalabel FILTER(lang(?jalabel)="ja") }`
to `TITLE_SPARQL` and re-run pass 2 for Wikidata. The response cache is keyed on URL plus body, so
a changed query is a fresh key and the existing entries are untouched; it is one batched request per
60 titles, roughly four requests for the whole catalogue. Until then the size of this class is
unknown and the 20 live readings and 51 romanisations should be treated as unverified against their
keys.

### Fix

Select `?jalabel` in `TITLE_SPARQL` and apply the author path's own-label guard in `_title_fact`:
an alias match may confirm the item is a work of an accepted type, and may supply nothing else. On
the evidence of the author side, the rule earns its keep.

---

## 4. 〇 is a NUMBER, so the symbol guard does not see it

### What is stored

Two titles, `異種族女子に〇〇する話` and `限界OLと女子大生が〇〇する話`. Both held
`… ニ レイキゴウ スル ハナシ` and `… ガ レイキゴウ スル ハナシ`. Curation has replaced both readings
with the mark kept verbatim; the analyser values survive in `reading_conflicts`, and the stale
`furigana_spans` still carry `['〇〇', 'れいきごう']` in both records.

### The line responsible

`adapters/names/pass4_analyser.py`, line 216 in `analyse` and line 408 in `furigana_spans`, the
same test written twice:

```python
if all(unicodedata.category(c)[0] in "PZS" or c.isascii() for c in surf):
```

The comment above line 216 states the problem this guard exists for: Sudachi does not decline to
read a symbol, it returns キゴウ, the reading of the word 記号. The guard passes punctuation,
separators and symbols through as themselves.

`〇` is U+3007 IDEOGRAPHIC NUMBER ZERO, and its Unicode general category is **Nl**, Number-letter.
It is not P, Z or S, and it is not ASCII, so the guard does not fire and the token goes to Sudachi:

```
異種族女子に〇〇する話  ->  ('〇〇', 'レイキゴウ', ('名詞', '数詞'))
```

Sudachi has `〇〇` as a numeral whose reading is 零記号, "zero symbol". The review's description of
it as the character's Unicode name is close enough to be useful and not quite right: the string is
Sudachi's dictionary reading, and it coincides with the Unicode name because both are describing a
zero sign. Either way it is not something anyone says.

The category test is the whole of the bug. The visually identical `○` (U+25CB, category So) and
`◯` (U+25EF, So) both DO hit the guard and pass through untouched, which is why
`異種族女子に○○する話`, the same work under the other spelling, came out correctly as
`イ シュゾク ジョシ ニ ○ ○ スル ハナシ`. One work, two spellings, two different outcomes from one
line.

### How many others

A census of all 2,043 names the pipeline holds (titles, authors and `data/build/series.json`)
found `〇` U+3007 in exactly **two** names, four occurrences, both reported. `○` and `◯` appear in
three further names and are all handled correctly.

The only other character in the whole corpus that escapes the guard and is not a kanji, kana or
ASCII is `々` (U+3005, Lm), nine occurrences, which is a kanji iteration mark and SHOULD be read.
So the guard is wrong about exactly one character in the current data.

Two follow-on points:

- The stale `furigana_spans` are dead rather than harmful. `build.py:650` already discards spans
  that do not reconstruct the stored reading, and れいきごう does not reconstruct 〇〇, so the ruby
  is re-derived from the corrected reading. But nothing UPDATES `furigana_spans` when curation
  replaces a reading, so `titles.yaml` now holds two records whose spans contradict their own
  reading and are silently thrown away every build. That is worth its own fix.
- `curate.py`'s `KATAKANA` pattern (line 90) already admits `〇○◯` into a reading, with a comment
  saying a censoring mark stays verbatim. The policy was written down; pass 4 does not implement
  it.

### Fix

Widen the guard to cover the mark rather than the category. The narrow form is an explicit set of
censoring and decorative characters checked before the category test:

```python
UNREAD = set("〇○◯×＊*※")
...
if surf and all(c in UNREAD or unicodedata.category(c)[0] in "PZS" or c.isascii() for c in surf):
```

applied at both line 216 and line 408, which must keep agreeing or one record gets two different
readings (the comment at line 404 says so). The broader form, treating category Nl as unreadable,
would be wrong: 々 is Lm and 〇 is the only Nl here, so a category rule buys nothing over the set.

---

## 5. `_REVERSE` gives "wo" to ウォ before を can claim it

### What is stored

Five titles, all `reading_basis: back-converted`, all `reading_source: mangaupdates`, all pass 2:

| title | stored reading |
|---|---|
| あなたが私を変えたから | アナタ ガ ワタシ **ウォ** カエタカラ |
| あなたの未来を許さない | アナタ ノ ミライ **ウォ** ユルサナイ |
| この恋を星には願わない | コノ コイ **ウォ** ホシ ニ ワ ネガワナイ |
| オタクには人生を積むことしかできない | オタク ニ ワ ジンセイ **ウォ** ツム コト シカ デキナイ |
| カナリアは綺羅星の夢をみる | カナリア ワ キラボシ ノ ユメ **ウォ** ミル |

All five are live. No author record is affected.

### The line responsible

`adapters/names/kana.py`, lines 330 to 333:

```python
_REVERSE = {}
for _k, _r in list(DIGRAPH.items()) + list(BASE.items()):
    _REVERSE.setdefault(_r, _k)
_REVERSE.update({"n": "ん", "shi": "し", "chi": "ち", "tsu": "つ", "fu": "ふ", "ji": "じ"})
```

DIGRAPH is iterated first and `setdefault` keeps the first writer, so `"wo"` is claimed by
`"うぉ": "wo"` (line 91), the katakana digraph for the foreign sound in ウォーター. BASE never
contests it, because BASE spells the particle `"を": "o"` (line 67), the Hepburn romanisation. So
`"wo"` is reachable only through ウォ and `を` is unreachable from any romaji at all:

```python
>>> kana._REVERSE["wo"]
'うぉ'
>>> kana.romaji_to_kana("Anata ga Watashi wo Kaeta kara")
'アナタ ガ ワタシ ウォ カエタ カラ'
```

Note that this is not a collision the tables could have caught: `set(DIGRAPH.values()) &
set(BASE.values())` is empty. The forward direction is correct in both tables. Only the reverse
merge is wrong, and it is wrong by iteration order.

Two other tables in the same codebase already say `wo` is the particle: `kana.PARTICLES` (line
281) and `pass2_bulk.JA_PARTICLES` (line 90). `_REVERSE` is the odd one out.

### How many others

Five stored readings, and that is the whole of the live damage. But the cause is broader than the
five:

- Across all 1,896 distinct MangaUpdates romaji strings in the cache, **21** contain the particle
  `wo` and all 21 back-convert to ウォ. Sixteen of them belong to titles we do not hold, or were
  outranked, or never matched. They are the same fault waiting on the same code.
- All 21 are the particle. None is a foreign ウォ. So the ambiguity the current mapping is
  presumably defending against does not occur in this data.

The corpus has no settled convention for the particle either, which is worth recording separately.
Among the 91 titles whose surface contains を and whose reading is stored:

| written as | count | bases |
|---|---|---|
| ヲ | 78 | analyser 71, researched 4, surface 3 |
| オ | 7 | back-converted 5, researched 2 |
| ウォ | 5 | back-converted 5 |
| neither (を dropped) | 1 | no reading basis recorded |

ヲ is the house form, and it is Sudachi's, since `PARTICLE_SOUND` (pass4_analyser.py:61) converts
は to ワ and へ to エ and deliberately leaves を alone. The seven オ come from sources that wrote
`o` rather than `wo`, which is unrecoverable: a romanised `o` cannot be told from the particle.

### Fix

One entry on line 333, which is the line that already exists to disambiguate exactly this kind of
reverse collision:

```python
_REVERSE.update({"n": "ん", "shi": "し", "chi": "ち", "tsu": "つ", "fu": "ふ", "ji": "じ",
                 "wo": "を"})
```

Verified against the whole cache: of the 1,896 romaji strings, 21 change and all 21 are corrected.
Nothing else moves. The five stored readings become ヲ, matching the 78 the file already holds.

The cost is that a genuine ウォ can no longer be recovered from a macron-less romanisation. That is
the lossiness the module docstring already declares back-conversion to have, and it is why the
basis is `back-converted` and outranked by anything kana. Writing a foreign ウォ as を is also the
smaller of the two errors: it misspells a loanword, where the current behaviour turns a particle
into a syllable the sentence does not contain.

---

## Two things the checks would need in order to have caught any of this

`check.py` has `inv_readings_are_kana` (line 137) and `inv_ruby_spells_reading` (line 74). Neither
compares a reading to the NAME it is stored under, which is the axis all of faults 1, 2 and 3 fail
on. The mora-band test in section 1 is the cheapest available form of that invariant and separates
the two length faults from 32 correct readings with no misses; it would not have caught fault 2,
which nothing downstream can catch.

`furigana_spans` is written only by pass 4 (lines 357 and 515) and is never updated or cleared when
`store.record` or `curate.py` replaces a reading. `build.py` compensates by discarding spans that
do not reconstruct the reading, so the page is right, but `titles.yaml` accumulates ruby that
contradicts its own record. Clearing `furigana_spans` whenever `reading` changes would make the
file mean what it says.
