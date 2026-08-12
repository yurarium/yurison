# One volume set per work: a plan

Written 2026-08-12 from three faults the project owner found on MURCIÉLAGO, a fourth found on
コミック百合姫 the day the second fix shipped, and a fifth the third fix caused. All of them are
classes rather than cases. §1 to §5 are done. What remains is the dating: the ISBN-keyed
catalogues are exhausted and 2,514 volume rows carry no date, because the shop that holds most of
them states no ISBN and nothing keyed on one can reach them. §6 asks the National Diet Library,
which is keyed on a title, and §7 asks コミックシーモア for what is left.

The sections below are in the order they are to be done, and each one says what it needs from the
one before it.

## 0. The faults, and why they are one job

**A volume is a thing.** It has a designation, a date, sometimes an ISBN, and several catalogues
describe it. Everything here follows from the corpus not modelling it that way: BOOK☆WALKER's
listing position was published as the volume's number, a volume record's own words never reach the
page, two catalogues describing one volume are shown as two volumes, and the catalogue that knows
the answer is never asked.

A NUMBER IS ONE KIND OF DESIGNATION AND NOT THE ONLY ONE, which §3 is where the plan learned. A
volume can be `3`, or `下`, or `2017年1月号`, and the last of those is a label and not a position in
a sequence. Reading it as a sequence is how a magazine came to have 119 volumes.

| | stage | needs |
|---|---|---|
| §1 | Measure what the shop says against what we hold | done 2026-08-12 |
| §2 | Stop publishing a listing position as a volume number | done 2026-08-12 |
| §3 | Carry what a record says about a volume, and read a designation as what it is | done 2026-08-12 |
| §4 | Render a field before drawing it, and prove a ruling that says nothing draws it | done 2026-08-12 |
| §5 | One volume row per volume, however many catalogues describe it | done 2026-08-12 |
| §6 | Ask the National Diet Library, which is free and keyed on a title | §5 |
| §7 | Ask コミックシーモア for what NDL could not answer | §6, which is cheaper |

§3 was found by a reader looking at コミック百合姫 the day §2 shipped, and it is the general fault
that page is one instance of: the build carried five of a volume record's fields and dropped the
two that would let a reader see anything about a volume nobody dated.

§4 IS §3'S OWN FAULT AND IT IS LIVE. The field §3 added is drawn with `esc` and reaches no
renderer, so 383 works show Japanese in English mode, and neither of the two guards that exist to
make that impossible could see it: both read the surface table, and the ruling §3 gave the field
says nothing draws it. That is a ruling nothing verifies, which makes §4 a structural repair and
not a patch.

**Measuring comes first, and this is the part that was nearly left out.** Each fix moves a number
nobody is currently watching, so each can regress into a state that looks exactly like the state it
fixed. §1 costs little, needs nothing built, and is what makes the repairs provable rather than
asserted. It is also the fastest way to find out how large §7 really is, and §2's own error was
caught by it within the hour.

---

## 1. Measure what the shop says against what we hold

**DONE, 2026-08-12.** `adapters/shopjoin.py` and four budgets in `docs/budgets.json`.

### The join

`shopjoin.py` asks in two ways and neither of them is a bare title, because a title identifies
nothing: `トワ・エ・モア` is a 1996 コンパス anthology and a 2024 講談社 series at once.

| route | what it settles | rows |
|---|---|---|
| a shared ISBN | an ISBN identifies an edition, so the same one is the same book | 543 |
| title AND house | the title says which work, the house says whose | 751 |
| declined | a title agreeing where the house does not | 35 |
| unjoined | works we do not hold, which is what the admitted queue is for | 502 |

Neither accepted route reaches two works for any row. The 35 declined are almost all
クロスフォリオ出版 and ナンバーナイン against works whose records name somebody else, and their
titles are `放課後`, `先生`, `少女レター`, which is exactly the shape the ISBN rule exists to
refuse.

**Two refusals were found by writing the test and are the reason the first numbers were wrong.**
コミックシーモア files `まんがの作り方【お試し版】` as a series of its own, holding one volume where
the work has eight; both carry the work's ISBN, so both join, and reading the sample's count as the
work's turned an agreement into a disagreement of 8 against 1. `counts_volumes` declines a sample
or a 分冊版 for the same reason `bwingest.CHAPTERWISE` declines to call 単話 a 巻. Separately, six
works are reached by two real rows each (`Qualia -Envy-` and `-Jealousy-`, two 編 of
`ネイルちゃんと深爪さん。`): those are different products under one identity, so the shop is not
stating how long the work is and neither count is taken.

### What the measurement says

| | |
|---|---|
| works exactly one cmoa row speaks about | 1,270 |
| counts that agree | 1,170 |
| **we hold FEWER volumes than cmoa states** | **70** |
| **we hold MORE than cmoa states** | **30** |

The two directions are different faults and are counted apart. Holding fewer is a stale capture,
which §7 fixes by asking: 冷たくて柔らか is 4 against 7, きみが死ぬまで恋をしたい 9 against 11.
Holding more is §2's fault showing through, a product count published as a volume count:
**MURCIÉLAGO 32 against 29**, citrus+ 8 against 7, 鎧塚さんをバブらせたい 6 against 4. The ISBN
route reaches MURCIÉLAGO, which a title fold could not, because cmoa spells it `MURCIELAGO`.

### The budgets, with their opening values

| budget | opens at | expected floor |
|---|---|---|
| `volume rows with no publication date` | 2,525 of 6,153 | falls as §7 collects |
| `works whose records number one volume twice` | 20 | **10**, see below |
| `works holding fewer volumes than the shop states` | 70 | falls as §7 collects |
| `works holding more volumes than the shop states` | 30 | near 0 after §2 |

**The floor of 10 is real books and was found by the canary.** The first version of this plan said
the second budget goes to 0 with §5. It does not: citrus really was printed twice, ten volumes in
2013 and four in 2015, MADB gave it two C-numbers for that reason, and a reader should see both.
Ten of the twenty are that (citrus, ゆるゆり, five 合本版 omnibuses, a 総集編, and two works under
two publishers); the other ten are one run described by two catalogues, which is what §5 resolves.
The measure asks the dumber question, whether any two of a work's records number one volume alike,
and leaves the difference to this paragraph. Asking which catalogue each record came from would
separate the two populations cleanly, and it is the rule the fix will use, so a measure asking it
would share the fix's blind spot.

**This also settles a question §5 had left open.** Ten works numbering a volume twice from two
different catalogues is the population the cross-catalogue merge was written for and withdrawn
from, on 2026-08-12, because merging blocks without reconciling volumes drew a 52-row MURCIÉLAGO
list. Once §5 reconciles the volumes, that withdrawal's reason is gone and the same-catalogue
exception is what keeps citrus apart.

Two further measures belong to the stages that create them and are written in the same change as
the fix each one guards, which is the rule `./test.py` already enforces for a new module and its
test. They are §2's invariant and §5's arithmetic, described in place below.

---

## 2. BOOK☆WALKER's volume number is the item's position in a shop listing

**DONE, 2026-08-12.** `adapters/facts/volumenumber/` reads the number the shop wrote, `bwingest`
uses it, and `a volume number is the shop's own` is an invariant. MURCIÉLAGO is 29 volumes.

### What is wrong

`adapters/bwingest.py:152` reads:

```python
row = {"number": i if len(work.get("volumes") or []) > 1 else None, ...}
```

`i` is `enumerate`'s index. It is published as the volume number, and the shop's listing is neither
a volume list nor in volume order.

MURCIÉLAGO is the whole fault in one record. BOOK☆WALKER lists 32 products under the series:

| position | product | what it is |
|---|---|---|
| 1, 2 | `MURCIELAGO -ムルシエラゴ- 1巻`, `2巻` | volumes 1 and 2 |
| 3, 4 | `… 1巻【無料お試し版】`, `2巻【無料お試し版】` | free samples of volumes 1 and 2 |
| 5 | `… 3巻` | volume 3 |
| 6 | `… 3巻【無料お試し版】` | a free sample of volume 3 |
| … | | |
| 32 | `【最新刊】… 29巻` | volume 29, delivered 2026-07-24 |

32 products minus 3 free samples is 29 volumes, which is exactly what the shop's own last item
says and exactly what コミックシーモア states. The corpus publishes `n: 32` and numbers the
volumes 1 to 32, so volumes 30, 31 and 32 exist in the interface and nowhere else, every number
after position 2 is off by one to three, and the dates sit beside the wrong numbers.

パロスの剣 is the same fault without the samples: the shop lists `【最新刊】パロスの剣 3巻` first,
so volume 3 is published as volume 1 and volume 1 as volume 2. 54 records disagree with their own
titles today, across 138 volume rows.

### The root fix

**The shop states the number in the product's own title, and that is the only number it states.**
A new `adapters/bookwalker_number.py` (or a function in `bwingest`, if it stays small) reads it,
and `volumes_of` uses it. A position is never a number.

Several forms need reading. Measured over the 628 multi-volume BOOK☆WALKER records, 2,922 volume
rows:

| form | example |
|---|---|
| `N巻` trailing | `MURCIELAGO -ムルシエラゴ- 29巻` |
| `（N）` trailing | `花の三騎士 （1）` |
| bare full-width trailing | `わたし、二番目の彼女でいいから。 ２` |
| `上` / `下` | `夢の端々（下）`, `お江戸とてシャン〈完全版〉下` |
| number then a subtitle | `ゆりぜん〜… 1巻〈夢に破れて、拾われて〉`, `… #3 リボンの天使は飛べない` |
| decimal | `ラブスコア9.1` |

A shop badge is not part of the title and comes off first: `【最新刊】`, `【最終巻】`,
`【期間限定無料】`. 58% of the rows state a number this way. `bwingest.NUMBERED_OFF` already holds
the reasoning for where a trailing number is a number and where it is a name (`あやめ14`,
`魔法少女201`, `再録集4`), so the extractor is that rule read forwards instead of backwards, and
there must be one copy of it, not two.

Where the shop states no number, the volume has no number. The interface already handles that
case ("A VOLUME NOBODY NUMBERED SAYS NOTHING", `20-app.js`), and §5 gives another catalogue the
chance to supply one. 196 multi-volume records state no number on any row; several of those are not volume
sets at all (`bw-217047` bundles three different works under one series id), which is worth knowing
and is currently hidden behind invented numbering.

**A free sample is not a volume.** `【無料お試し版】`, `【試し読み】` and their kin are excluded from
`volumes` and from `volume_count`, the way `CHAPTERWISE` already excludes 単話 and 分冊版. 13
records hold 16 such products today. The counter-case to check before writing the rule is
`【期間限定無料】`, which marks a real volume that is temporarily free rather than a sample edition.

**`volume_count` becomes the count of volumes**, not of products, and where numbers are stated it is
the count of distinct numbers.

### Evidence to keep in the test

`bw-15279` (samples and a `【最新刊】` last), `bw-22410` パロスの剣 (`【最新刊】` first, so position
order is wrong), `bw-84256` なないろ黒蝶 (listing order 1, 3, 2, 4), `bw-394812` 『citrus +』小冊子
(the number in the title is the PARENT work's volume and must not be read), `bw-223949` ゆりぜん
(number before a `〈〉` subtitle), `bw-89b2ebd2…` ステラのまほう (one volume, full-width `１巻`).

### The measure that guards it

**`a volume number is the shop's own`**, an INVARIANT and not a budget, at 0 from the day it landed.
A position published as a volume number is a fault in the pipeline every time, not a deficit that
research reduces.

It asks a dumber question than the name in the plan suggested. "Was this number read or assigned"
cannot be asked of the data, only of the code that wrote it, and a check that re-ran the reader
would share its blind spot. What it asks instead is whether the number a record states occurs in
that volume's own product title at all, NFKC-folded so a full-width `１` meets a stored `1`. Every
form of the fault fails that test: the sample numbered 3 for coming third, パロスの剣's volume 3
numbered 1 for being listed first. It is pure substring arithmetic over two shipped fields.

### What landed, and what it moved

| | |
|---|---|
| the series title is inside the product title | 94% of 4,792 rows |
| a number is read from the title | 81% of rows; 719 of 963 records fully numbered |
| free samples dropped | 29 products |

**The series title turned out to be the evidence, not the pattern.** The plan expected the reader to
be `bwingest.NUMBERED_OFF` read forwards. It is not, and the difference is what made it work: a
rule reading digits off the end of a title has to guess whether they are a number or a name, and
`あやめ14` and `ラブフェロモンNo.5` are names. A product title in a series is the series title with
something added, so removing the series name leaves exactly the something and there is nothing left
to guess. `NUMBERED_OFF` stays, because naming a work the shop holds one volume of is a different
question with different evidence.

The comparison had to be made tolerant of accent, width, case and punctuation before it worked at
all: BOOK☆WALKER files the series as `MURCIÉLAGO -ムルシエラゴ-` and the volume as `MURCIELAGO
-ムルシエラゴ- 1巻`. And the imprint has to come off the series title first, which is 3,634 of the
4,792 rows: a series filed as `さかさまロリポップ（まんがタイムKRコミックス）` names its volumes
`さかさまロリポップ　１巻`.

**A count of distinct numbers was wrong and the shop said so.** The first version counted distinct
stated numbers as the volume count, so 魔法少女三十路, which lists seven volumes and numbers one of
them, came out as one volume against コミックシーモア's seven. 17 works moved the wrong way and
§1's budget caught it within the hour. A volume nobody numbered is still a volume; what it lacks is
a name for its place in the run. The count is distinct numbers plus the items carrying none.

| budget | before | after |
|---|---|---|
| `works holding more volumes than the shop states` | 30 | **25** |
| `works whose records number one volume twice` | 20 | **15** |
| `works holding fewer volumes than the shop states` | 70 | **68** |
| `volume rows with no publication date` | 2,525 | **2,521** |

MURCIÉLAGO's index row now reads 29. Its work page still draws two runs, 29 volumes and 20, which
is §5 and is untouched here.

---

## 3. A volume record says more than the build carries, and a designation is not always a number

**DONE, 2026-08-12.** Found on コミック百合姫 by the project owner the day §2 shipped. The page reads
`収録号 119` over 117 named, dated issues, and 0 rows in the corpus are now counted without being
listed.

### What is wrong

The magazine's page reads, in full:

```
VOLUMES 119
119 with no date and nothing else recorded
```

§2 stopped publishing the listing position as a volume number, and `volumenumber` declines a
periodical, so the 119 rows lost the only field they carried. The interface then asks
`says = v.published || v.isbn || v.number || editions.length`, and a row failing it is counted
rather than listed.

**§2 removed no true information here.** The page previously read `vol. 1` … `vol. 119`, which was
the shop's listing order asserted as volume numbers of a magazine, with "no date recorded" beside
every one. What went was the pretext keeping the rows visible.

WHAT WENT MISSING LONG BEFORE THAT is in `build.py:3221`, which builds a volume row out of five
keys:

```python
m = {k: … for k in ("madb_id", "number", "isbn", "published", "published_basis") if k in v}
```

`title` and `delivered` are dropped there, and the shop states both for all 119 issues. This is not
a magazine fault:

| | |
|---|---|
| volume rows a reader can reach | 6,150 |
| rows the page counts but cannot list | **1,420**, across 897 works |
| of those, whose source record states a delivery date | **1,420** |
| of those, whose source record states the product's own title | **1,420** |

Every silent row in the corpus has two facts in its source record that the build discards.
コミック百合姫 is the largest single instance, at 119; ゆるゆり 小冊子 has 17 and
まんがタイムきららＭＡＸ 13.

### What an issue designation is, ruled by the project owner 2026-08-12

**`2017年1月号` IS AN OPAQUE STRING AND IS NOT A DATE.** It is what the issue is called. It is not
parsed, nothing is derived from it, and no issue is dated by it. The corpus treats it exactly as it
treats a title.

The reason is that a magazine's designation scheme is not stable across its own run, so nothing
read out of one form carries to the next. コミック百合姫 has used at least four:

| era | how an issue was designated | schedule |
|---|---|---|
| earliest | `Vol. 7 Winter 2007`, a position and a label together | quarterly |
| then | the same volume numbering | bimonthly |
| then | no volume number at all | bimonthly |
| now | `2017年1月号` | monthly |

A `Vol. 7` from 2007 and a `2017年1月号` do not belong to one sequence, so neither ordering nor a
gap means anything across the join. The label is carried and nothing is derived from it, which is
all this stage has to do about it: a designation nobody can order is one nobody will try to.

**AND THE DELIVERY DATE IS NOT THE ISSUE'S DATE EITHER.** 2017年1月号 was delivered 2016-11-18;
2026年9月号 on 2026-07-16. The cover date leads the on-sale date by about six weeks throughout,
which is the ordinary Japanese magazine convention. It is also the same publisher, 一迅社, whose
発売日 against 奥付 gap `isbndate.py` already measures and refuses to use as a sharpening. Two facts
about one issue, and neither is a more precise version of the other. The delivery date travels as
itself, under its own label, exactly as `delivered_from` already does at the block level.

That is the whole of it: **carry what the record says, and say what it is**. There is nothing to
parse, which makes this the smallest of the five stages.

### A free issue is not a sample, and this sharpened a rule §2 shipped

`えっちな百合姫【無料版】` and `ほんのり百合姫【無料版】` are two of the 119, and they are whole
chapters selected from various works rather than the opening pages of one. They are issues that
happen to be free. §2's `SAMPLE` rule excludes `お試し版` and `試し読み` and deliberately leaves
`期間限定無料` alone, and this says why that is right in a way the rule did not: what disqualifies a
product is being **a fragment of a volume**, not being free. The rule needs no change and the count
of 119 stands, as 117 dated issues and 2 free ones.

### The root fix, which is corpus-wide

**Carry `title` and `delivered` onto the volume row**, and show them where a row would otherwise
show nothing. That is one line in `build.py` and one predicate in the interface, and it reaches
1,420 rows across 897 works rather than one magazine. A row's own label is displayed unparsed, which
is what the owner's ruling above requires and what makes this stage small.

### A position in a sequence, or a label

THE LINE RUNS BETWEEN A DESIGNATION THAT NAMES A POSITION IN A SEQUENCE AND ONE THAT IS A LABEL,
where this stage first drew it between books and magazines. `3`, `下` and `創刊号`
are positions and are read as such. `2017年1月号` is a label and is carried whole. A magazine can
use either, and コミック百合姫 has used both in its own lifetime.

**ガレット settles it, ruled by the project owner 2026-08-12.** Its numbering is consistent, and
its odd row is `創刊号`, which is Vol. 1 said in words. The corpus holds `No.2` through `No.37`
numbered and `創刊号` alone unnumbered, so reading it restores the sequence rather than interpreting
anything: 創刊号 means the inaugural issue, which is the first. It joins `上` and `下` as a
designation written in words, and `volumenumber.ISSUE`, which currently declines it, is wrong to.

WHICH LEAVES THE PERIODICAL MARK A SMALLER JOB THAN THIS STAGE FIRST GAVE IT. Nothing needs to be
kept out of ordering or gap-checking by being a magazine, because those key on a number and a label
is not one. What the mark decides is what the page CALLS the list: `収録巻` over 117 issues of a
magazine is the wrong word, and it is the wrong word whether or not they are numbered. So ガレット
is a periodical whose issues are numbered, コミック百合姫 is a periodical whose issues are labelled,
and the two questions are independent.

The signal is the open question. BOOK☆WALKER tags 117 rows `[雑誌]`, all of them コミック百合姫's,
which is certain and narrow; a date-shaped designation reaches 141 rows across 5 records, which
catches まんがタイムきららＭＡＸ and ちゃおデラックスホラー but says nothing about ガレット, whose
rows look exactly like a book's.

### The measure that guards it

**`volume rows a page counts but cannot list`**, a budget that opened at **1,420** and stands at
**0**. §1's `volume rows with no publication date` does not cover it: a row can carry a date and
still show a reader nothing, and 119 of them did.

It counts, over works.json, what the interface's own `says` would decline to list, and the two
predicates are written out separately on purpose: one decides what a page draws, the other what the
build owes it. `test_interface.py` reads the served `app.js` and asserts they name the same fields,
because they stopped agreeing once already and that is how 119 rows went missing.

### What landed

| | |
|---|---|
| rows the page counts and cannot list | 1,420 → **0** |
| issues of コミック百合姫 named and dated | 117, plus the 2 free ones |
| records the shop tags a magazine | 1, and only that one is marked |

**`創刊号` moved from being declined to being read, and then to being kept as written.** The first
attempt returned `1`, which put a number in the record that the product title does not contain, and
`a volume number is the shop's own` caught it inside a minute. The record now keeps the shop's own
word and `build.volume_number` turns it into 1, which is where `vol. 8` and `第1巻` already become
integers. ガレット reads `vol. 1` through `vol. 37` with a stated gap at 10 and 11.

The delivery date is shown and says what it is: `on sale 18 Nov 2016` / `配信 2016年11月18日`, in
its own class, dimmer than a publication date. コミック百合姫's 2017年1月号 was delivered six weeks
before its cover date, so a delivery date labelled as a printing would be wrong by that much on
every issue.

**One limit was accepted rather than guessed past** and is recorded in `docs/GAPS.md`: only
コミック百合姫 is tagged `[雑誌]`, so ガレット, まんがタイムきららＭＡＸ and ちゃおデラックスホラー
are magazines still headed as volumes. Inferring the format from a date-shaped designation would
find two of those, miss ガレット, and mark whatever else happens to be named by a date.

### What is out of scope, and is a coverage note rather than a debt

BOOK☆WALKER holds コミック百合姫 from 2017年1月号. The magazine began in 2005, no catalogue in the
corpus holds the earlier run, and MADB's コミック百合姫 records are books under that imprint rather
than issues of the magazine. That is a known and probably permanent gap in what is reachable, which
belongs in `docs/GAPS.md` and not in a budget that could never fall.

---

## 4. A field ruled as undrawn, and drawn

**DONE, 2026-08-12.** The leak is closed and the ruling that hid it is now checked against the
source. `ゆるゆり 特装版小冊子電子版` reads `Yuru Yuri Tokusō Ban Shōsasshi Denshi Ban`.

### What is wrong

`kari/src/20-app.js` draws a volume's designation like this:

```js
: (v.designation ? `<span class="voln vdesig">${esc(v.designation)}</span>` : '');
```

`esc()` straight into the markup, through no renderer. 899 of the 987 designation rows hold
Japanese, across 383 works and 845 distinct strings, and every one of them is on an English page.
`ゆるゆり 特装版小冊子電子版` is how the project owner found it.

### Why both guards were blind, which is the part that matters

The structure is meant to make this impossible. `interface.unruled` forces a decision on every
field the data carries Japanese in, and the decision has two answers: a **Surface**, which names
the function that renders the field, or **NOT_A_NAME**, which says nothing draws it. A Surface is
then held two ways, by `English mode has no Japanese` running the real renderer over every value
and by `adapters/lint/entrypoints.py` proving that `kari/app.js` never puts the field on a page any
other way.

Both of those read `interface.SURFACES`. **A NOT_A_NAME path is never compared against app.js at
all**, so the second answer is asserted and never verified. The ruling and the check share the
author's belief, which is STANDING-INSTRUCTIONS §14b in the one place the project had assumed it
was safe. `entrypoints.py`'s own docstring states the assumption without noticing it: "a field the
build writes and the interface never reads is not a leak", which is true and establishes nothing.

**AND IT IS NOT ONE FIELD.** Asking the entrypoints tokeniser which NOT_A_NAME values are escaped
into markup or interpolated returns twelve:

| what they are | fields |
|---|---|
| deliberate verbatim quotes | `first_publication.note`, `marketing_label_basis.note`, `evidence[].source`, `state_claims[].source` |
| a Japanese-side aid | `index[].y` |
| values that carry no Japanese | `releases[].id`, `channel_name`, `completed_basis`, `cadence` |
| a leak | `works[].volumes[].designation` |

NOT_A_NAME is carrying two different rulings in one list: *nothing draws this* and *this is drawn
verbatim on purpose*. Only the prose in each entry tells them apart, and prose is not enforcement.

### The work

1. **Close the leak.** Render the designation through `phraseOf`, which is where `volLabel` already
   sends a named part, and feed designations into `fill_chapters` the way §3 fed volume numbers.
   The analyser answers usefully on a sample: `#1 るっく・あっと・みー/…` comes out
   `Ch. 1 Ru Kku Atto Mī / …` and `2017年1月号` comes out `2017 Nen 1 Gatsu Gō`. About 845 entries,
   all derived, so it is a build run rather than research.
2. **Split the ruling vocabulary.** `NOT_DRAWN` for a field nothing puts on a page, `QUOTED` for one
   drawn verbatim on purpose with its reason and the language it is drawn in. Re-file the 46
   existing paths; the twelve above are the ones needing a decision rather than a move.
3. **Enforce the second half.** `entrypoints.py` gains the job it never had: a `NOT_DRAWN` field
   whose read is consumed by `esc` or a template interpolation is a finding. `QUOTED` gets the
   narrower check that it is drawn only where its reason says.
4. **Prove the hole is shut by reopening it.** The canary is `esc(v.designation)` restored, planted
   in `entrypoints.py`'s self-test beside the four historical faults it already replants.

### Why it is not reverted

Reverting §3's designation display would put 383 works back to `N with no date and nothing else
recorded`, which is the state the owner reported. The render path exists and the phrase map is
filled by a pass that already runs, so closing the leak is the shorter road as well as the better
one. Ruled by the project owner 2026-08-12.

### What landed

**One entry point for what a volume row is called.** `volLabel` takes the number where there is one
and the designation where there is not, because they are the same question, and drawing them
separately is what let one of them onto the page unrendered. The designation goes through
`phraseOf`, and `build.py` feeds designations into the analyser pass beside the numbers §3 added.
**899 of the 901 Japanese-bearing designations are rendered from the phrase map**; the two left are
Chinese editions of Japanese works whose titles hold both scripts, and they floor and are marked.

Getting there took three findings the owner's reading of the page produced.

**A title's bracket and the shop's bracket are different sets.** The 17 ゆるゆり booklets came out
with one name between them, because every title after its leading `「…」` reads
`ゆるゆり 特装版小冊子電子版` and the aside-stripper took the bracket off. BOOK☆WALKER writes its
own marks in `【】` and `[]`; a title writes in `「」` and `〈〉`. Reading a NUMBER still strips both,
because a number is never inside either.

**A volume designation is not a credit field, and the pass was guessing that it might be.**
`fill_chapters` declines to render a credit line, correctly, because romanising `[著]中村明日美子`
as one run is the fault in its worst form. It decides by asking `is_credit_line`, which answers yes
to `Walking the Underground - 地底をゆく` and to `2019年1月号増刊(2018年12月20日発売)`, so 158
designations got no rendering on the strength of a guess about a population they are not in. The
caller now says which it is.

**A rendering that is still Japanese is not a rendering.** The analyser handed back one Chinese
title with its full stops narrowed, which passed the `en != x` test and went into the map;
`kari/app.js` refuses such an answer when reading, so the row was one the interface ignored and
`kana left in a romanisation` counted. The store now applies the reader's own rule.

**The ruling split in two.** `interface.NOT_DRAWN` is 31 paths, each now a claim about
`kari/app.js` that `entrypoints.undrawn_findings` verifies. `interface.QUOTED` is the 14 that
really are drawn as the source wrote them, each carrying why: `index[].y` behind `LANG !== 'en'`,
the evidence notes, a chapter identifier, four tooltips. `NOT_A_NAME` remains as the union, so the
readers that only need to know a path is accounted for did not change.

Every one of the 14 turned out to be legitimate, which is worth saying plainly: the audit found one
leak and it was the new field. What was wrong was not the rulings but that nothing could tell a
right one from a wrong one.

**The gap is closed by the lint that already existed for the other half.** A read of a `NOT_DRAWN`
field consumed by `esc` or a template interpolation is a finding, which is the same pair
`_refuse_bad_safe` has always treated as the definition of reaching a page. `entrypoints.py`'s
self-test plants this afternoon's fault beside the four historical ones: the ruling moved back and
the call site restored, both halves of what went wrong.

It cannot tell two rulings apart when they share a field name, since the accessor is the last
segment: a third `source` under a `NOT_DRAWN` path would be allowed by `evidence[].source` being
QUOTED. The fault it exists for is a NEW field name drawn without a renderer, which no other ruling
covers, and that is the shape the designation had.

### The measure that guards it

`entrypoints.py` is an INVARIANT and not a budget, for the reason it already was one: a field
reaching a page without its renderer is a fault every time. Item 3 widened what it asserts rather
than adding a number.

---

## 5. Two catalogues describing one volume are drawn as two volumes

**DONE, 2026-08-12.** MURCIÉLAGO is one list of 29 volumes, each carrying the day-precise date
BOOK☆WALKER states and the ISBN MADB states.

### What is wrong

20 works carry records that number the same volume more than once, 73 volume numbers in all. The
cause is that a volume is never reconciled: each catalogue record keeps its own volume list and the
interface concatenates them. MURCIÉLAGO holds

- `C338361` (MADB + openBD): volumes 1 to 20, ISBNs, month precision, so `1` is `2014-04`
- `bw-15279` (BOOK☆WALKER): the same books, no ISBN, day precision, so `1` is `2014-04-25`

so the page shows `vol. 1 April 2014` and `vol. 1 25 Apr 2014` and calls them two runs. The print
block merge shipped on 2026-08-12 stops short of this deliberately, and `build.py`'s `print_runs`
records why: merging the two blocks without merging their volumes drew a 52-row list.

The interface has a volume dedup already (`20-app.js`, `merged`), and it cannot reach this: it
merges only within one record, and only where the number AND the date agree exactly. Two catalogues
at two precisions agree on neither field.

### The root fix

**One volume row per (run, number), built where the run is built.** In `build.py`, beside
`merged_print_block`: fold the volume lists of a run's records into one set keyed on the volume
number, and give each row

- the number, from the catalogue that states one, a bibliography's or a shop's own volume index
  ahead of a shop listing;
- one date to show, plus the basis that says where it came from;
- every ISBN seen, which the interface already renders as `editions`;
- any date that could not be reconciled, kept as its own field rather than dropped
  (STANDING-INSTRUCTIONS §1: record a disagreement, do not discard it).

**The date rule already exists and must not be written a second time.** `adapters/isbndate.py`
draws exactly the distinction this needs: `2014-04` against `2014-04-25` is one fact at two
precisions and the finer form is taken; `2013-05` against `2013-06-02` is two sources disagreeing
and the held value stands. It is currently used only for the MADB↔openBD join inside one record.
`resolve` is keyed on nothing but the two date strings, so the cross-record merge can call it
directly, and the basis vocabulary (`cmoa_volumes.PREFERENCE`) is already shared.

What the merge must NOT do is reconcile a delivery date against a publication date. `delivered` is
the day a shop began selling a file and `cmoa_volumes` measures a worst case of 128 months between
the two; it travels as `delivered_from` with its own label and is never a candidate for the shown
date.

**A reissue is still two runs.** `print_runs` decides that already, on overlapping numbering, and
this changes nothing about it: citrus's 2015 reissue is a second run whose volumes merge among
themselves. The 20 works measured above are the ones where two catalogues describe ONE run, and
they are the whole population of this fix.

**The interface's cross-record dedup can then go**, because there will be nothing left for it to
do, and a rule that no longer fires is a rule that will drift.

### What it fixes beyond the duplicates

`index.json` takes its `n` from the union of distinct volume numbers, so MURCIÉLAGO's `n: 32`
becomes 29 as soon as §2 lands and the union is taken over reconciled numbers. Six works currently
show two runs that are one run described twice (MURCIÉLAGO, 白き乙女の人狼, トワ・エ・モア,
おやすみシェヘラザード, 監獄街へようこそ!, お姫様のお姫様 among them).

### The measure that guards it

**`volume numbers a page draws twice`**, opening at **5**, the arithmetic STANDING-INSTRUCTIONS
§14b wants beside §1's count of works numbering a volume twice: it counts the rows a work page
would DRAW, not the records behind them, so a merge that folds the blocks and leaves the volumes
doubled cannot pass. That is the check that would have caught the 52 row MURCIÉLAGO list without
anyone opening the page. Its floor is those 5, each a second printing with its own ISBN whose date
disagrees, which `merge_volumes` refuses to fold and a reader should see.

### What landed

| budget | before | after |
|---|---|---|
| `works whose records number one volume twice` | 15 | **8** |
| `volume rows with no publication date` | 2,521 | **2,514** |
| `volume numbers a page draws twice` | new | **5** |

**The rules the merge decides by, each found by a case.** A date at two precisions is one volume,
through `isbndate.resolve`; a date that disagrees is a second printing and stays its own row, which
is 君と綴るうたかた's volume 6 in 2024-03 and again in 2025-01-13. The same number on the same day
is one volume in two editions, which is ささやくように恋を唄う and is the fold `kari/app.js` used to
do: that code is gone, because doing it in two places would be two producers of `editions` and the
browser's copy could not see across records anyway.

**A run of one record is still a run**, which is what let the interface stop folding volumes at all.

**Some rules had to be sharpened before the counts came right.** A record holding one unnumbered
volume claims volume 1, so MADB's two マーメイドライン records are a book and its 2019 reissue rather
than a two volume work. A record holding SEVERAL unnumbered volumes is its own run, because its
rows cannot be reconciled with numbered ones: 白き乙女の人狼 came out eight volumes long where both
catalogues say five. And where a run's numbering is incomplete the row count is not its length, so
the largest count a record states about itself stands.

**Four budgets rose and were accepted**, all from one cause: 2,551 print blocks where there were
2,457, because reissues and unnumbered runs are now separated rather than folded together. Three of
them count per block (`an imprint field repeating its publisher` 341 to 360, `imprint strings that
reach no line` 16 to 18, `titles read by a machine, unmarked` 1,470 to 1,477) and one is a single
work moving into `works holding fewer volumes than the shop states`.

---

## 6. The National Diet Library is free, keyed on a title, and already half-wired

Needs §5. Ruled ahead of コミックシーモア by the project owner 2026-08-12: scraping a shop for an
ISBN and a date is expensive, and anything NDL can answer should be asked of NDL first.

### Why this is the route, in one measurement

Every volume row that has an ISBN has a date, and every row that has a date has an ISBN. The two
populations are the same 2,305 rows, which is the whole story: dating is ISBN-keyed, and
BOOK☆WALKER states no ISBN on any of 5,968 volumes read. **The ISBN-keyed databases are exhausted**
and the wall is the key, not the catalogue. openBD is asked for every ISBN the corpus holds, the
MADB bulk release agrees with all 2,286 dates and adds nothing because the corpus was read off
those records, cmoa's `printed` agrees on all 538 it shares, and the publishers' own pages and
Books.or.jp took the 49-row residue.

NDL is the one public database with a different key. `adapters/ndl.py` searches by TITLE with author
agreement and returns `dcndl:volume`, `dcterms:issued`, the ISBN and the publisher per volume, which
is every field this needs. It is a national library, it is free, and it holds every book published
in Japan.

**THE POPULATION IS THE ROWS WITH NO ISBN AND NOT THE ROWS WITH NO DATE**, which is a correction
the project owner made on 2026-08-12 by asking whether NDL holds MURCIÉLAGO's later volumes. It
does: `Murciélago` volumes 1 to 28, with an ISBN and an issued date on every one, where MADB stops
at 20. This plan had scoped NDL at 818 rows by asking which UNDATED rows no catalogue reaches, and
three filters that were each defensible alone threw most of the population away between them.

| | rows | works |
|---|---|---|
| volume rows with no ISBN | **3,733** | |
| no bibliographic record for the work | 3,710 | 1,541 |
| the catalogue knows the work and stops short | 23 | 8 |

An ISBN is worth more than a date, because it is the key every other enrichment needs: openBD,
the MADB 単行本 dataset and `isbndate.resolve` are all keyed on one, and 3,733 rows can reach none
of them. Supplying the ISBN opens all of those at once.

The 23 are small in count and are the case that found the error: a running series whose
bibliographic record lags the shop. MURCIÉLAGO's volumes 21 to 29 are 9 of them, and NDL has 21 to
28 catalogued.

WHAT IS STILL A FLOOR. cmoa states no ISBN for 1,215 of its 1,833 works, led by ナンバーナイン at
580 and クロスフォリオ出版 at 164, digital distributors whose books were never printed. No
bibliographic database holds a book with no ISBN, and NDL will not either. What was wrong was
treating "cmoa reaches this work" as evidence about NDL, which it is not.

AND NDL LAGS THE NEWEST VOLUME. MURCIÉLAGO's 29th was delivered 2026-07-24 and the catalogue holds
to 28, 2026-01. A pass that ran monthly would pick each one up a few months late, which is the
ordinary state of a national library and not a reason to prefer a shop.

### The pass has been rejecting almost every match, and it is one character

Four probes against the live API, chosen from the works above:

| we hold | NDL writes |
|---|---|
| `司馬舞` | `司馬, 舞` |
| `よしむらかな` | `よしむら, かな` |

`ndl._fold` removes spaces and not the comma, so the author filter answered 0 on every probe that
had a real match to find. `MURCIÉLAGO -ムルシエラゴ-` returned 20 items including four volumes of
its own BYPRODUCT spin-off, correctly authored, and every one was thrown away.

That fold is also a private copy of a fact `facts/namekey` owns. `loosely` is the matching key and
already removes the bracketed apparatus and the interpunct, which are the same judgement: a
separator a catalogue puts between the family name and the given name. The comma belongs beside
them, and `ndl.py` should ask rather than keep its own.

### The other quirks the probes found

**NDL rewrites the title into ISBD form.** `アラーニァ : murciélago byproduct`, with the subtitle
after a colon and the Latin lower-cased. `facts/cataloguing` already owns that split, for MADB, and
is the module to ask.

**A shop's decorations are not in it.** `【単行本】`, `単話版` and `-ムルシエラゴ-` are BOOK☆WALKER's;
`bwingest.strip_imprint` and `volumenumber` already take those off, and the title to search with is
the one the work is held under rather than the one a product is sold under.

**A title search matches every book in Japan.** `わくとこまこ` returned 12 items and
`MURCIÉLAGO -ムルシエラゴ-` returned a paper on Calakmul's dynastic succession. The author
agreement is not an optimisation, it is what makes the answer mean anything, which `ndl.volumes`
already says.

**A record with no ISBN is not a volume record.** `わくとこまこ` returns twelve items numbered 1 to
11 with no ISBN and no issued date, which is the serialisation rather than the books.
`ndl.volumes` already drops them.

**The date is written `2022.9`.** It needs normalising to the corpus's form before
`isbndate.resolve` can compare it with anything.

### The work

1. **Fix the fold and remove the copy.** A comma between name parts joins the interpunct in
   `namekey.loosely`, with the counter-case tested, and `ndl.py` asks that instead of folding its
   own. This is the whole of why the route looks empty.
2. **A volume pass over the works whose rows carry no ISBN**, searched by the work's own title,
   filtered by author agreement, normalising `2022.9` to `2022-09`. NDL returns `dcndl:volume` as
   well, which is the volume NUMBER: that answers the 19% of BOOK☆WALKER product titles §2 cannot
   read a number out of, and the counting question §7 was going to cmoa for.
3. **Join what comes back by ISBN**, which is what §5's merge is already keyed on, so a dated NDL
   volume lands beside the shop's row rather than beside it as a second list.
4. **Then §7 asks cmoa only for what is left**, which is the ordering the owner ruled.

### The measure that guards it

`volume rows with no publication date`, which stands at **2,514**, and a new companion counting
**volume rows with no ISBN**, at **3,733**. The second is the one that measures this pass: an ISBN
answers the date through openBD and MADB by itself, so a row that gains one usually gains both.
Their shared floor is the books that have no ISBN to be catalogued under.

---

## 7. コミックシーモア knows the volumes and is never asked about a work we hold

Needs §5, or it adds a third overlapping volume set to the two already double-counted.

### What is wrong

`data/queue/cmoa-volumes.yaml` holds 1,833 works read off cmoa's 百合・GL shelf. For 1,831 of them
the shop states its own volume count, and the volume list is numbered by the shop rather than by a
listing position. MURCIÉLAGO's row says 29 volumes, correctly numbered 1 to 29, and has said so all
along.

None of it reaches a work we hold. `data/source/` has no `cmoa/` directory: the capture feeds the
admitted queue, whose rows are dropped once the work is attested from another source, and
`shopfinal.py` reads it for completion claims keyed on ISBN. So the one catalogue that could have
told us MURCIÉLAGO has 29 volumes was on disk while the interface said 32.

The dates are half-collected for the same reason. cmoa's per-volume page states 出版年月 and an
ISBN; the capture opens volume 1's page and stops, because `volumes_outstanding` exists to fill the
inclusion test and volume 1 answers it. 5,429 volume pages have never been opened, 839 of them
belonging to works whose volume 1 states an ISBN, and MURCIÉLAGO's volumes 2 to 29 are 28 of those.

Meanwhile 2,525 volume rows a reader can reach carry no publication date at all, 41% of the 6,153,
and every single one of them comes from a BOOK☆WALKER record. BOOK☆WALKER states no ISBN
on any volume, so nothing keyed on an ISBN can reach them and no enrichment pass has ever been able
to help. cmoa's page is the route: it states the ISBN, and once the ISBN is known openBD and the
MADB 単行本 dataset date it, both of which are already wired.

### The root fix

**Run the volume pages.** `cmoa_volumes.py --volumes` already does this; what is missing is the
scope. Today `printed_only=True` asks only about works whose volume 1 states an ISBN, which is the
right economy for the inclusion test and the wrong one for dating a work we hold. The scope becomes:
a volume page is worth opening where the work is one we HOLD and the volume has no date. That is a
bounded job: 839 pages under the current filter, and the held-work filter is a different and
probably smaller set.

Then make cmoa a source rather than only a queue: a `data/source/cmoa/` record, written by the
same capture, in the shape the other retailer records already have (`data/source/bookwalker/` is
the model). Then
the volume set of a held work can carry cmoa's statement, `print_runs` and the §5 merge treat it as
one more catalogue of the same run, and the reconciliation rules apply to it without a second
mechanism. Joining is by §1's join, which is why §1's join has to hold.

**The volume COUNT is a claim in its own right**, and §1 has already made it one. Under
DEFINITIONS §5 a retailer is Tier C, so it is a lead, and a lead a person can act on is a check.
That check would have caught MURCIÉLAGO's 32 against 29 on the day the record was written, which is
the argument for doing §1 before anything else rather than after everything.
