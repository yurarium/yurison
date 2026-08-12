# One volume set per work: a plan

Not started. Written 2026-08-12 from three faults the project owner found on MURCIÉLAGO, all of
which are classes rather than cases. The work page currently shows that work as two runs of 32 and
20 volumes, numbers its volumes wrongly, invents three that do not exist, and leaves 41% of every
volume row in the corpus with no date beside it.

The sections below are in the order they are to be done, and each one says what it needs from the
one before it.

## 0. The faults, and why they are one job

**A volume is a thing.** It has a number, a date, sometimes an ISBN, and several catalogues describe
it. Everything here follows from the corpus not modelling it that way: BOOK☆WALKER's listing
position is published as the volume's number, two catalogues describing one volume are shown as two
volumes, and the catalogue that actually knows the answer is never asked.

| | stage | needs |
|---|---|---|
| §1 | Measure what the shop says against what we hold | done 2026-08-12 |
| §2 | Stop publishing a listing position as a volume number | §1, to see what it moves |
| §3 | One volume row per volume, however many catalogues describe it | §2, for numbers to key on |
| §4 | Ask コミックシーモア about the works we hold | §3, or it adds a third overlapping set |

**Measuring comes first, and this is the part that was nearly left out.** Each fix moves a number
nobody is currently watching, so each can regress into a state that looks exactly like the state it
fixed. §1 costs little, needs nothing built, and is what makes the other three provable rather than
asserted. It is also the fastest way to find out how large §4 really is.

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
which §4 fixes by asking: 冷たくて柔らか is 4 against 7, きみが死ぬまで恋をしたい 9 against 11.
Holding more is §2's fault showing through, a product count published as a volume count:
**MURCIÉLAGO 32 against 29**, citrus+ 8 against 7, 鎧塚さんをバブらせたい 6 against 4. The ISBN
route reaches MURCIÉLAGO, which a title fold could not, because cmoa spells it `MURCIELAGO`.

### The budgets, with their opening values

| budget | opens at | expected floor |
|---|---|---|
| `volume rows with no publication date` | 2,525 of 6,153 | falls as §4 collects |
| `works whose records number one volume twice` | 20 | **10**, see below |
| `works holding fewer volumes than the shop states` | 70 | falls as §4 collects |
| `works holding more volumes than the shop states` | 30 | near 0 after §2 |

**The floor of 10 is real books and was found by the canary.** The first version of this plan said
the second budget goes to 0 with §3. It does not: citrus really was printed twice, ten volumes in
2013 and four in 2015, MADB gave it two C-numbers for that reason, and a reader should see both.
Ten of the twenty are that (citrus, ゆるゆり, five 合本版 omnibuses, a 総集編, and two works under
two publishers); the other ten are one run described by two catalogues, which is what §3 resolves.
The measure asks the dumber question, whether any two of a work's records number one volume alike,
and leaves the difference to this paragraph. Asking which catalogue each record came from would
separate the two populations cleanly, and it is the rule the fix will use, so a measure asking it
would share the fix's blind spot.

**This also settles a question §3 had left open.** Ten works numbering a volume twice from two
different catalogues is the population the cross-catalogue merge was written for and withdrawn
from, on 2026-08-12, because merging blocks without reconciling volumes drew a 52-row MURCIÉLAGO
list. Once §3 reconciles the volumes, that withdrawal's reason is gone and the same-catalogue
exception is what keeps citrus apart.

Two further measures belong to the stages that create them and are written in the same change as
the fix each one guards, which is the rule `./test.py` already enforces for a new module and its
test. They are §2's invariant and §3's arithmetic, described in place below.

---

## 2. BOOK☆WALKER's volume number is the item's position in a shop listing

Needs §1, so that the 30 works holding more volumes than the shop states can be watched falling.

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

**Where the shop states no number, the volume has no number.** The interface already handles this
("A VOLUME NOBODY NUMBERED SAYS NOTHING", `20-app.js`), and §3 gives another catalogue the chance to
supply one. 196 multi-volume records state no number on any row; several of those are not volume
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

**`volumes numbered by a listing position`**, an INVARIANT and not a budget, at 0 from the day this
lands. A position published as a volume number is a fault in the pipeline every time, not a deficit
that research reduces. Counted by asking each BOOK☆WALKER volume row whether its number was read
from the product title or assigned.

---

## 3. Two catalogues describing one volume are drawn as two volumes

Needs §2. A volume set cannot be merged on numbers that are positions.

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

**`volume rows the interface shows twice`**, the arithmetic STANDING-INSTRUCTIONS §14b wants beside
§1's count of works numbering a volume twice: count the rows a work page would DRAW, not the records behind them, so a
merge that folds the blocks and leaves the volumes doubled cannot pass. This is the check that
would have caught the 52-row MURCIÉLAGO list without anyone opening the page.

---

## 4. コミックシーモア knows the volumes and is never asked about a work we hold

Needs §3, or it adds a third overlapping volume set to the two already double-counted.

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

**Make cmoa a source, not only a queue.** A `data/source/cmoa/` record, written by the same capture,
in the shape the other retailer records already have (`data/source/bookwalker/` is the model). Then
the volume set of a held work can carry cmoa's statement, `print_runs` and the §3 merge treat it as
one more catalogue of the same run, and the reconciliation rules apply to it without a second
mechanism. Joining is by §1's join, which is why §1's join has to hold.

**The volume COUNT is a claim in its own right**, and §1 has already made it one. Under
DEFINITIONS §5 a retailer is Tier C, so it is a lead, and a lead a person can act on is a check.
That check would have caught MURCIÉLAGO's 32 against 29 on the day the record was written, which is
the argument for doing §1 before anything else rather than after everything.
