# Which things are works, and what a record may claim about one: a plan

Written 2026-08-13 out of the session that took `works without English` to zero. Four of the five
items below were found by doing that work rather than by looking for them, and the fifth is a
question the project owner raised about a category the work exposed. None of them is a case; each
is a class with a number beside it, measured today.

The sections are in the order they are to be done, and each says what it needs from the one before.

| | stage | needs | measured today |
|---|---|---|---|
| §1 | Run the name passes as part of the update | nothing | 96 works had no English for want of this |
| §2 | A claim about a reading stops occupying the English's slot | nothing | 196 titles, 1,337 authors |
| §3 | A work attested on a platform we already read gets a page | a ruling on §3b | 53 works |
| §4 | Join a translated edition to the work it translates | nothing | 28 products, 7 unjoined |
| §5 | Two capture faults on the credit field | nothing | 4 rows |

## 0. What connects them

**A record is entitled to say exactly what its source said, in the slot that fact belongs in.**
§2 and §5 are that rule broken in the small: an analyser's doubt about a reading written where the
argument for an English name goes, and a page title written where an author goes. **A thing the
corpus knows about is either a work or it is out of scope, and something has to decide which.**
§3 and §4 are that question unanswered in two directions, one letting works fall through and the
other letting one work in five times.

§1 sits at the front because it is the reason §2 was invisible. A pass nobody runs produces no
number that moves, so the store drifts and every check reads healthy.

## 1. Run the name passes as part of the update

**THE FAULT.** `works without English` stood at 96 on 2026-08-12, and 95 of those works had a title
the platform prints in Latin, needing no research at all: `Distortion`, `GIRL FRIENDS`, `Girl@Girl`.
`pass0_cache` had a rule for exactly that case and had simply not been run. Nothing said so, because
the budget was recorded at 96 and a budget that ratchets down reads as satisfied at its recorded
value.

`build.py` imports `pass4_analyser` for its functions and never runs a pass. `adapters/stage-a.yaml`
runs thirteen capture adapters and no name pass. So a work entering the corpus on a Monday carries
whatever name the store already held, which for a new work is nothing, until somebody runs
`resolve.py` by hand.

**WHAT TO DO.** Add the free passes to the update, in the order `resolve.py` already uses: pass 1
before pass 0, because pass 1's readings are `surface` and outrank everything, so pass 0 gets a
smaller queue. Then `pass4_analyser`, then `curate.py --apply`.

The awkward part is the cost. Pass 0 walks the whole capture cache: 131,784 files and
about twenty-five minutes, almost all of it looking for author handles on pages, which is worth
doing weekly and wasteful daily. Its first step, the surfaces that need no romanising, costs
milliseconds and is what a daily run needs. Split the two, or gate the walk on a `--since`, and the
daily cost falls to nothing.

**HOW IT IS PROVED.** `works without English` is already 0 and recorded, so it can only rise.
A work arriving unnamed now moves a number the same day rather than whenever somebody looks.

## 2. A claim about a reading stops occupying the English's slot

**THE FAULT.** `pass4_analyser` writes, at both of its two write sites,

    rec["note"] = ("reading guessed by a morphological analyser, not stated by any source; "
                   "analysers are weakest on pen names and coinages")

`note` is the field that says why the ENGLISH is what it is. `reading_note` is the field for a
claim about the reading, and `adapters/names/curate.py` explains at length why the two are separate:
one entry can carry two decisions, and 55 of 60 reading corrections landed on titles that already
had a curated translation with its own argument.

The assignment overwrites whatever is there, so **196 titles hold a curated English name with a
sentence about morphological analysis where its argument should be**. `#We're the Strongest`,
`A 14-Gram Escape` and `4:30, at the Laundromat` were all translated by somebody who wrote down why,
and the store says none of it. 341 title records and 1,337 author records carry the sentence in
total; the rest of them have no curated English, so the slot was empty and the loss is smaller.

**WHAT THIS COSTS TODAY.** Nothing a reader sees: the field reaches no page. What it costs is the
next reviewer, who opens a record to find out why a title reads as it does and is told about
SudachiDict. `facts/reading/vocabulary` already exists to decide which words the analyser was
actually guessing at, and its own docstring quotes this sentence as the justification for the
unverified mark, so the sentence is load-bearing in its right slot and misleading in this one.

The fix is to write `reading_note`, and only where nothing has been written there. Leave `note`
alone. Then sweep the store once: a record whose `note` is exactly this sentence and whose
`reading_note` is empty moves it across; a record whose `note` is this sentence and which holds a
curated English keeps the curated argument, which it never had.

**THE COUNTER-CASE TO TEST.** A title whose `en` came from the romanisation itself, where the
sentence in `note` was doing double duty legitimately. It still belongs in `reading_note`, and the
English's slot should then be empty rather than wrong, which is the honest state and is what §1's
budget will show as work to do.

## 3. A work attested on a platform we already read gets a page

**THE RULING, given by the project owner 2026-08-13:** the category of works living only in the
release feed should essentially not exist by construction. A new work from a platform we already
know about, arriving by an attesting route, presumptively gets its own work page.

**THE FAULT.** `build.py` builds the series index from one record type:

    if _d.get("record_type") != "web_work_chapters": continue

Four web routes write attesting records and one of them can produce a work page.

| route | works it names | with no work page |
|---|---|---|
| `web_work_chapters` | 1,522 | 170, held out by rules that are about something else |
| `work_update_dates`, ニコニコ漫画 | 486 | 76 |
| `web_series`, publisher yuri labelling | 165 | 13 |
| `web_releases`, GigaViewer Atom | 30 | 6 |

So 53 works are attested on a platform we already read and hold no chapter-level record anywhere,
and nothing in the pipeline can ever give them a page. 47 reach us only through ニコニコ's work-level
dates and 6 only through a GigaViewer Atom feed. They include
`わたしが恋人になれるわけないじゃん、ムリムリ！（※ムリじゃなかった!?）`, `おちこぼれフルーツタルト`
and `見える子ちゃん`, which are not obscure. A reader meets each of them on the releases page, follows
nothing, and the work is absent from every list the site draws.

**§3a. THE SIX ARE MECHANICAL.** A GigaViewer Atom record carries the episode title, the date, the
author and the URL for every release, which is what a row is made of. They assemble from what is
already on disk.

**§3b. THE FORTY-SEVEN NEED A RULING, and it is the reason this section has a dependency.**
`work_update_dates` is `granularity: work` on purpose: ニコニコ漫画 states that a work updated on a
date and never which chapter, so the record attests an update and nothing about its contents. A
series row's shape assumes a chapter list, and the chapter count, the access mode, the free-view
tally and both the first and latest date all read that list. Those 47 rows would carry an episode
count and no chapters.

The row should exist and say plainly that the platform attests the work rather than its contents,
which is the move `provenance` already makes elsewhere. What needs deciding is what the work page
draws where the chapter list goes, and whether a chapterless row is allowed into counts that are
currently statements about chapters. **Settle §3b before building §3a**, so one shape serves both.

The 170 are a different question and stay out of this section. They hold chapter records and are
held out by the app-only rule, the catch-all resolver rule or the scope test, each of which is
deliberate and each of which deserves its own count before anything is changed.

## 4. Join a translated edition to the work it translates

**THE QUESTION was raised by the project owner 2026-08-13** as whether Korean editions should be
considered at all. Measured, the answer is already settled in practice and the remaining work is a
join that fails on a spelling.

BOOK☆WALKER sells translations of the same doujinshi as separate products. **28 of them**, under
six spellings of the marker, mostly English:

| | |
|---|---|
| 22 | `【English ver.】`, `【English Ver.】`, `【English ver】` |
| 3 | `【한국어 ver.】` |
| 2 | `【中国語版】` |
| 1 | `【Ver. en Español】` |

**THE CORPUS ALREADY TREATS ONE AS AN EDITION, and it is right to.** `w02056` holds three records
as one work: the Japanese `はずかしがりやのれいむさん`, the Chinese edition and the English edition.
Each product title pairs the translated name with the Japanese one across a hyphen, so the shop
states the relation itself.

That pairing is also **a route to an official English name, and 16 works already have one by it.**
`Reimu is Easily Embarrassed`, `BEAST MODE`, `Friendly Feuding Families`, `Nesting Crow` and twelve
more are recorded `official-jp` sourced to bookwalker.jp, because the publisher printed the English
beside the Japanese in one string. A translation made here would rank below any of them.

**WHERE IT FAILS, and this is the whole of §4.** The shop files the original of one work in kana,
`はずかしがりやのれいむさん`, and writes the base title of three of its translated editions in kanji,
`はずかしがりやの霊夢さん`. The English and Chinese editions quote the kana and joined. The Korean and
Spanish editions quote the kanji and did not, so they stand as works of their own, named
`Reimu is Easily Embarrassed (Korean edition)` and `(Spanish edition)` by a reviewer working around
a join that had already failed. `栖鴉` and `組長達のなかよし` each carry an unjoined Korean edition
the same way.

Counted across all 28: 16 name a base work that is held and joined, 3 name one held under a
different spelling, 4 name a base work absent from the corpus, and 5 carry no separator at all, so
nothing can be split out of the product title.

An unjoined edition credits its translators as authors of the work.
`【한국어 ver.】부끄럼쟁이레이무씨` credits `あとき / 싱글벙글환상향 / 어쟤예쁘네 / 그냥계정`, where the
three Hangul names are the circle that translated it, and the Spanish edition credits
`Ｈｏｕｒａｉ　Ｄｏｌｌ` beside あとき. Those are claims about who made the work. Joining the edition
puts them where a translator belongs; leaving it unjoined needs a role on the credit instead.

**WHAT TO DO.** Match the base title through a fold that equates a kana spelling with its kanji one,
which is what these three need and nothing else in the corpus currently asks for. Then the 4 whose
base work is absent are the only open question, and it is a small one: whether a translated edition
may be the only record of a work we hold no Japanese record for.

**THE COUNTER-CASE TO TEST.** A product whose base title matches a DIFFERENT work by the same
circle. The join is on a title inside a title and a doujinshi circle publishes many, so a match that
skips the creator would merge two works by あとき into one.

## 5. Two capture faults on the credit field

Small, found in passing, and left here so they are not found again.

**A PAGE TITLE IN THE AUTHOR FIELD.** Two コミックゼノン release rows carry
`レオパード・ゲッコー / 読切 画家の肖像` and `ぽぽらら / 読切 散らないで菊`, which is the artist, a
separator, and the work's own page title. `split_authors` then reads the second half as a person, so
the corpus gains a credit named after a chapter. The interpunct in `レオパード・ゲッコー` is also
split, which put ゲッコー and レオパード into `author names romanised as one word` as two people on
2026-08-13.

An author is absent where the platform states one. `ツイてるギャルとミエてる陰キャ` arrived from
きら星ポータル with an empty author, and the page reads `著者：深水たろー` and
`©深水たろー／COMICメテオ`. `横槍メンゴ新作読切シリーズ` from ヤンジャン+ is the other, and there the
artist's name is in the work's own title. 2 rows of 983 in the feed window, so the class is small and
the fix is per-adapter.

**HOW BOTH ARE PROVED.** `incomplete attested rows` already counts a release missing a chapter name,
an author or an access state, and stood at 37 on 2026-08-13. Neither of these fault classes moves it,
since one row has an author that is wrong rather than absent and the other is counted already.
A count of credits holding a chapter marker would see the first.

## What is already in hand

The National Diet Library run from VOLUMES-PLAN §6 is still going, at 1,512 works asked of about
1,541 and 397 answered. §6 item 4 and §7 pick up from its output and are unaffected by anything
here.
