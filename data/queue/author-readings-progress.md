# Author readings pass, 2026-08-06 — checkpoint

Task: settle author readings from stated sources. Two routes.

1. openBD collationkey (publisher stating how its own author is read) over every ISBN the corpus
   holds. `reading_basis: stated`, `reading_source_kind: publisher-jp`.
2. GAPS §9: a Latin name the person writes themselves. `basis: stated`, `source_kind: author`.

Cache: ../names-cache/openbd.json, seeded from ../openbd-cache (410 ISBNs, 275 held).

## State at start (data/names/authors.yaml, 1757 names)

| reading_basis | n |
|---|---:|
| analyser | 873 |
| stated | 538 |
| surface | 276 |
| none | 65 |
| back-converted | 5 |

`en basis`: romaji 1690, stated 65, official-jp 1, none 1.

## Log

- Read the authority documents.
- Offline run of openbd_reading.py: 873 guessed, 122 on a book we hold an ISBN for, 302 ISBNs.
  Health refused, because offline cannot tell an uncached ISBN from one openBD does not hold.
- Widened `openbd_reading.py`: `corpus_isbns()` asks over every ISBN any source record states
  (1363) instead of only the ISBNs MADB files under a credit we hold (302); `unsettled_readings()`
  selects on nothing having stated a reading rather than on an analyser having guessed one;
  `normalised()` declines a collationkey that has lost a kana name's own kana.
- Fetched: openBD holds 1115 of 1363. 104 readings settled, all `stated` / `publisher-jp`.
- Appended those 104 plus とりい しづく (surface) to data/names/curated.yaml. `--check` clean at
  1182 titles, 584 authors.
- NEXT: apply, rebuild, gate. Then GAPS §9, the Latin names people write themselves.
- Applied. Store: stated 538 -> 642.
- `curate.py` could not record what GAPS §9 asks for. `ATTRIBUTION["stated"]` listed platform and
  publisher-jp and not `author`, so an entry attributing a Latin byline to the artist's own page
  was rejected outright. The row's own comment says "the person's own rendering, where they wrote
  it". `author` reached SOURCE_KINDS and READING_ATTRIBUTION in a round about readings and this
  list was edited apart from them. Added, with the case in test_curate.py.
- Found while ranking authors: 181 kana-only author names carried an `analyser` reading. Pass 1
  answers those exactly and for nothing, but the autopilot in build.py only ever runs pass 4, and
  pass 4 queued on "has no reading". Three were wrong on the live site: はうあゆ as Wa u Ayu,
  はとぼし as Wa Toboshi (an analyser takes は as the particle) and あーねすと as アー ネ ストッ.
  Fixed in pass4_analyser.wants_reading, calling pass1_kana.surface_fields rather than repeating
  it. Scoped to authors: 6 kana TITLES have the analyser right, because in a sentence は IS wa.
- Corpus regenerated under this run (BOOK☆WALKER imprint suffixes retracted, 93 duplicate works).
  Re-read titles.json: 3144 titles, curated keys still all match, 0 stray.
- Autopilot bug found and fixed: a `reading_refuted` record has no reading, and `fill_missing`
  read that as an empty slot. Ten refuted names were refilled with the guess a reviewer had just
  disproved, 古川楊也 back as フルカワ ヨウナリ within hours. `wants_reading` now declines them.
- GAPS §9: 犬井あゆ -> Ayu Inui and 野宮りおん -> Rion Nomiya, both `stated` off クロスフォリオ出版's
  own English editions, corroborated by NDL's reading. Merged into their existing entries rather
  than appended, which would have dropped their NDL readings under a duplicate key.
- Shelf trap recorded in curated.yaml: 179 of 976 BOOK☆WALKER credits carry a separator and the
  part after it is the circle, not the person.

## Finished 2026-08-06

- `./test.py`: 84 passed, 0 failed, 0 vacuous, 0 unproven.
- `./check.py --gate`: 0 invariants violated. One budget over, `stock phrasing in comments`
  897 against 896. Not from this work: swapping every file this session touched for its HEAD
  version leaves the count at 897, and build.py alone is one LOWER than HEAD. Another session is
  working in that area.
- `uncertain readings` back to 64, on budget, after the refutation loop was closed.

---

# Author readings and missing credits, 2026-08-06 — second checkpoint

Two pockets: works crediting nobody, and readings no source states.

## Works crediting nobody: 103 -> 4

`adapters/bylines.py` reads the byline off the work's own page for the 49 web works, and
コミックシーモア's contributor line-up plus 一迅社's own book pages for the 49 print anthologies.
See the commit for the rules tried and rejected. Four are unresolved and each says what was
searched: プリンセ「ス」, Girls Love vol.2, Wildrose Re: mix and 百合姫selection.

## Readings: 609 unsettled -> 486

| route | settled | evidence |
|---|---:|---|
| MADB `ja-hrkt` creator transcription | 105 | `stated` / `national-library` |
| openBD, over the 40 ISBNs the corpus gained | 6 | `stated` / `publisher-jp` |
| ヤンマガWeb author pages | 9 | `stated` / `platform` |
| the artist's own site or link page | 3 | `stated` / `author` |

44 of the MADB 105 and 4 of the ヤンマガWeb 9 corrected the reading on display.

## Routes checked and closed, so the next pass does not pay for them again

- **NDL.** Still `Disallow: /api`, re-read from robots.txt on 2026-08-06.
- **openBD.** Asked about every ISBN the corpus states. Exhausted until the corpus grows.
- **MADB.** Exhausted for the 486 that remain: they are web artists the catalogue has no book by.
  Re-run it whenever a MADB release is pinned or the corpus gains print works.
- **GigaViewer platforms.** となりのヤングジャンプ, サンデーうぇぶり, 少年ジャンプ+, コミックDAYS,
  くらげバンチ and 一迅プラス have no author page at all and answer a creator search with titles.
  カドコミ carries the name with nothing beside it. Only ヤンマガWeb, which runs its own engine,
  prints a reading, and its nine artists are done.
- **一迅社.** Its book database and its 百合姫 site carry contributor lists and no readings, which
  is why the anthology credits above came from it and no reading did.

## The artist's own page: measured, not estimated

Eleven of the most-published unsettled names were worked by hand. Three keep a page stating a
name: 焔すばる (Homura Subaru, so 焔 is ホムラ and not the ホノオ an analyser produced), 秋月ルコ
(AKIDZUKI Luco, her own spelling of ルコ) and 福井遥香 (福井 遥香（ふくい はるか）, HARUKA FUKUI).
Eight do not: 桜庭友紀, 雪尾ゆき, 河合朗, 浅海まい, 寝路, 須藤佑実, 沼地どろまる, 山葵るお have
an X account or a FANBOX and no page that says how the name is read. A handle is not a byline:
桜庭友紀 posts as @kyomoneko_2, which romanises nothing.

**So the rate is roughly one in four, and the residue is not a queue.** 486 names at one in four
is not a plan; it is the shape of the answer, and §5d's unverified mark is what those names are
for.

## The lead not taken, and why it is written down rather than run

まんが王国 (comic.k-manga.jp) prints a kana reading beside every author it lists:
「河合朗（かわいろう）」, which disagrees with the カワイ アキラ on display. コミックシーモア and
DMM do the same on some listings. A licensed retailer is not a community database, and
`curate.py` names "a bookshop listing" as evidence a reviewer may weigh under `researched`.

It was not run, for one reason: `researched` says a person weighed the evidence, and applying it
to four hundred names mechanically is a bulk import wearing a reviewer's label. It is worth doing
as a bounded round over the names where a shop's kana DISAGREES with the analyser, because those
are the readings a reader is being shown wrongly today, and each of those is a real judgement.
The shops also disagree with each other. DMM files 桜庭友紀 as さくらばゆうき where another
listing gives さくらばゆき, which is exactly why it cannot be taken in bulk.

## Groups that are not people

- `コミックニュータイプ(編)`, on 8 works, was rendering the magazine's editorial credit as a
  person: コミック ニュータイプ ( ヘン ), brackets and all. Refuted.
- `Be編集部`, on the four 百合＋カノジョ volumes, is the credit both shops give and is a department.
  Kept as the credit and listed under `not_a_person` in data/source/webpages/bylines.yaml.
- The 179 BOOK☆WALKER credits whose second part is a doujin circle never reached the store.
  `Ｍａｇｐｉｅ` and `Usagisan-Books` are in neither data/names nor the corpus, while あとき and
  やとさきはる are in as people. That trap is closed upstream and stayed closed.

## The shop states the TITLE's reading in a field, and again in the blurb

Found by the project owner and confirmed on the page. BOOK☆WALKER's `<meta name="keywords">`
carries the whole title's reading beside the title, and its description glosses a surname with
furigana in running text on first use. 豹藤さんは攻略（おと）したい states both:
`ヒョウドウサンハオトシタイ` in the field and `豹藤（ひょうどう）` in the blurb. The analyser had it
as ヒョウ フジサン ワ コウリャク シタイ, wrong on the surname and blind to the work's own gloss of
攻略 as おと, from 落とす.

`adapters/names/shop_reading.py` reads both, stores only the extracted pair and never the blurb
(REQUIREMENTS §2), and checks itself: the reading is the first katakana field that is not the shop
describing its own catalogue, the fields in front of it must rejoin to the title the page states,
and a volume number the shop appends to the reading comes off only where the title itself has no
trailing digits. 100日後に咲く百合 was otherwise about to be published as
Hyakunichigonisakuyuri001.

**1,548 of the 3,601 titles with no stated reading have a BOOK☆WALKER page**, so this is the
largest single route left in the naming work. 13 are settled. The shop answers slowly, roughly one
page every twenty seconds under a polite pause, so the remainder is a resumable run rather than a
finished pass. Settled is final, so restarting costs nothing.

It settles TITLES. The keywords field names the author and does not state the author's reading, so
it does nothing for the 486 names still outstanding.

## A credit made only of separators

Five works read `creator: " / "`, which is what `" / ".join(authors)` produces from an empty list.
It is not empty, so every count of works crediting nobody walked past them and the byline pass
never queued them. `adapters/bylines.credited` is the test now, and build.py uses it before falling
back, so a shop row with no authors in it is treated as the silence it is.

Four of the five were then settled off コミックシーモア, which files each anthology volume under
`アンソロジー` and names the artist on every 単話 it sells separately: one row per story. The
fifth, Yrhm百合姫20thアンソロジー, sells no 単話 and stays unresolved.

---

# Author readings, 2026-08-08: third checkpoint

The measure this round is against is what a READER meets, and it is now a budget so it cannot be
lost: `author readings no source states` counts authors in `data/build/feed/names.json` shipping
`basis: romaji` under the unverified mark. **769 at the start of the round and 309 at the end.**

Nothing about the mark changed. `build.py` clears it for `stated` and for `researched` and for
nothing else, so every one of those 460 names has a citation or an argument on its record now.

## What the corpus growing reopened

The second checkpoint recorded openBD and MADB as exhausted "until the corpus grows", and it grew:
the store went from 1,757 author names to 2,336, most of the difference from the ニコニコ漫画
serialisation pass. Both were asked again at no request cost, out of the caches already on disk.

| route | settled | evidence |
|---|---:|---|
| MADB `ja-hrkt` creator transcription, release 1.2.18 | 48 | `stated` / `national-library` |
| openBD collationkey, over 2,417 corpus ISBNs | 46 | `stated` / `publisher-jp` |

Four names came back from both and the two agree on all four. 90 distinct names, 62 of them names a
reader meets, so the number fell 769 to 703.

## NDL, measured and closed again

`/books/` record pages are open and answer 200, which contradicts what
`bookwalker-yuri-authors.yaml` recorded in August (503 on the HTML pages). The route is still shut,
for a different reason: `https://ndlsearch.ndl.go.jp/search?cs=bib&creator=` returns the identical
564,314 bytes whatever creator is asked about, because the document holds no results at all and the
records are fetched afterwards from `/api`, which robots.txt still disallows. There is no permitted
way to get from a person's name to a record id, so the open record pages cannot be reached.

Whoever resumes: the byte count is the finding. A page that answers 200 and states nothing looks
exactly like a creator the library has never catalogued.

## The lead the second checkpoint declined, taken as a bounded route

`adapters/names/kmanga_reading.py`. まんが王国 prints the kana in the byline of every title page it
sells: `<a href="/search/author/15404">甲斐谷忍<span class="f10">（かいたにしのぶ）</span></a>`, and
it prints nothing where it knows nothing. `researched` with `derived` beside it, never `stated`,
because a retailer does not say where its kana came from and the page cannot separate a publisher's
registered yomi from the shop's own filing key.

What makes it a route and not a bulk import: the shop's own spelling of the credit has to equal ours
before a book is opened and again after, each gloss is read out of the anchor its name sits in, two
books glossing one name differently settle nothing, and every entry carries the page, the book and
the string it replaces so the decision can be argued with.

All 761 names were asked, one request at a time, over about two hours in two sittings. The queue
is ordered by how many works credit the name, and the cache makes it resumable: the first sitting
was killed at 416 names and the second picked up from there at no cost for anything already asked.

```
python3 adapters/names/kmanga_reading.py --cache ../kmanga-cache --reviewed <today>
```

**418 settled, 328 the shop answered nothing for, 15 refused here.** 256 of the 418 agree with the
reading already on display, which is worth something on its own, and **158 disagree**, which is the
number that matters: those are names a reader was being shown wrongly. 上城たすく was ウエジョウ and
is カミジョウ. あまどり協奏曲 was ア マ ドリ キョウソウキョク and the work reads 協奏曲 as
コンチェルト. タイザン5 was タイザン 5 with the digit unread and is タイザンファイブ. 五葉 was ゴヨウ
and is イツハ.

## The negatives are written down, which no reading round had done

The 328 names the shop answered nothing for are in `data/names/attempts.yaml` under source
`k-manga`, so the next round does not spend 328 requests to be told the same thing. That file has
held this fact for pass 2 since August and no reading route had ever added to it.

Only a real answer is written off. A search that never came back and a reading refused here are
both left open, because `store.attempt` means the name is never offered again and a name written
off wrongly is not recoverable without an edit.

## Four refutations met new evidence, and one of them fell

生肉 was refuted in August as an unsupported セイニク, and the reviewer recorded the artist's X
handle, @namanoniku0005, with nothing to do with it. まんが王国 files them ナマニク. The handle
spells the same thing, the two were arrived at independently, and the refutation is now replaced by
a `researched` reading that cites both.

The other three stand and the shop's answer was declined. 伊実 is a Chinese creator NDL deliberately
files without kana. 時一二 is the same and the shop's シーイーアー is a transliteration of Shi Yi
Er. 角川青羽 is 角川青羽（上海）文化創意有限公司, a company, and カドカワアオハネ reads a corporate
body as a person.

Withdrawing a refutation exposed a fault worth having: `curate.apply` recorded one and could never
remove one, so the record ended up holding a reading AND the refutation of a reading, and
`pass4_analyser` reads that field to decide whether a name may be filled at all. Fixed with the
case in `test_curate.py`.

## A rule this round tried and dropped

The shop states no boundary between family and given name, which is the same silence MADB's
readings carry and is stored as it comes. Three readings had to be refused for it: 筋肉☆太郎 is
キンニクタロウ, and with no boundary in the kana the aligner had nothing to anchor on at the ☆, so
it put き over 筋肉 and んにくたろう over 太郎. `implausible ruby spans` went from 0 to 2 and caught
it. 中村 朱里 and 乃木 康仁 are the same shape with a space where the ☆ is.

The first rule written for it refused any reading that drops a mark the surface carries, and it is
wrong: 小鬼36℃ is コオニサンジュウロクド and 惚れた女の遺言.mp3 is
ホレタオンナノユイゴンドットエムピースリー, where the shop is reading the mark ALOUD, which is more
than any other source here does. `kmanga_reading.alignable` asks `kana.align`, which is the
function build.py will actually use, and applies the same arithmetic the budget applies.

## Routes still closed, so the next round does not pay for them again

- **BOOK☆WALKER author pages.** `bookwalker.jp/author/{id}` carries the name in the title, the
  description and the keywords field, and a reading in none of them.
- **コミックシーモア author pages.** `/search/author/{id}` states the name and no kana. Its keyword
  search is disallowed by robots (`/search/result/`) in any case.
- **DMM.** `/search/` is disallowed by robots, so the listings that carry kana cannot be reached.

## Two things another session's round put into this one

Recorded here because they arrived from outside and would otherwise be lost with the session.

**川村マユ見 is カワムラ マユミ**, and the National Diet Library says so on a record page that is
open: https://ndlsearch.ndl.go.jp/books/R100000001-I01211008001685179. Verified here rather than
taken on report. The 著者標目 field runs each contributor's name into its own reading and this one
reads `川村 マユ見 カワムラ マユミ`. `stated` / `national-library`, and it agrees with what the
analyser had.

That page also settles what the NDL section above could not. The record pages DO state author
readings, and every one of them is reachable if you have the record id. What is missing is a
permitted route from a person's name to an id, and it is missing for the reason given above.

**Twelve publisher records are people**, because a work self-published through a shop names its own
author as its publisher, and `publishers.english` consumes the author store. Ten of them are in this
population and so are settled by whatever settles them here: あおい華葉、さとうメメ子、夢乃むえ、
川村マユ見、河津ケント、珠虫さとり、赤月めう、雪尾ゆき、高橋真弥、高菜しんの. The other two,
とばり湊 and 井庭人, are in `data/names/publishers.yaml` and in no author record and no corpus
credit at all, so nothing on the author side can reach them.

**NDL rate-limits hard**, on that session's measurement: `/books/` answers 503 to anything faster
than roughly one request every few seconds, and a sweep of 124 ids took two hours with 61 answering.
A 503 is the server refusing and is not an absent record, so retry before concluding anything.
