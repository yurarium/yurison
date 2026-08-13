# Which things are works, and what a record may claim about one: a plan

Written 2026-08-13 out of the session that took `works without English` to zero. Four items below
were found by doing that work rather than by looking for them, and two came from the project owner
reading the result and asking what the categories it exposed actually meant. None of them is a case; each
is a class with a number beside it, measured today.

The sections are in the order they are to be done, and each says what it needs from the one before.

| | stage | needs | measured today |
|---|---|---|---|
| §1 | Run the name passes as part of the update | done 2026-08-13 | 96 works had no English for want of this |
| §2 | A claim about a reading stops occupying the English's slot | done 2026-08-13 | 196 titles, 1,337 authors |
| §5 | Two capture faults on the credit field | done 2026-08-13 | 4 rows |
| §3 | Fetch the episode lists we never asked for | done 2026-08-13 | 53 works |
| §6 | Ask the shops about a work, not only their yuri shelf | §3, which is the same move | 560 to ask about |
| §4 | Join a translated edition to the work it translates | done 2026-08-13 | 28 products, 7 unjoined |

**THE NUMBERS ARE THE ORDER THEY WERE FOUND IN, and the table above is the order to do them in.**
§3 and §6 both ADD works, which is what moved them down. A work arriving before §1 arrives unnamed,
before §2 it acquires an argument about the wrong fact, and before §5 it can bring a page title into
its own credit field. Fixing the intake first means the new works land clean rather than joining a
queue of repairs. §4 depends on nothing and can be done at any point.

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

**DONE 2026-08-13.** Stage E in `update.yml` runs pass 1, pass 0 with `--surfaces-only`, pass 4 and
`curate.py --apply`, after Compile because every pass takes its worklist from the build. A second
Compile follows only where the store actually moved. `data/names` joined the commit list, without
which the store would be rebuilt and thrown away every run.

Two things had to be fixed to run the passes the documented way, and both had gone unnoticed
because nothing ever ran them like this. `curate.py` imported `facts` above the `sys.path` line
that makes `facts` importable, so `curate.py --check` from the repo root, which is the usage in its
own docstring, died on ModuleNotFoundError. And the first version of the rebuild test asked
`git diff --quiet -- data/names`, which reports the store as changed on a run that named nothing:
`generated:` is a datestamp every compaction rewrites, and running the sequence by hand showed a
diff consisting of four dates and nothing else.

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

**DONE 2026-08-13.** Both write sites now offer `ANALYSER_CAVEAT` to `reading_note` with
`setdefault`, so a reading somebody has already reasoned about outranks a sentence about
SudachiDict. The sweep moved 1,693 records, 341 titles and 1,337 authors and 15 publishers, and
1,000 of them turned out to hold a real reading argument already, which was kept: `#うちらが最強`
keeps `陰キャ is いんキャ, an established coinage from 陰気なキャラ` and simply loses the misfiled
sentence. 693 records carry the caveat in its own slot now and 0 carry it in `note`.

359 titles now hold a curated English name with no argument beside it, which is the honest state
the counter-case above predicted. Each is work somebody can do. Re-running the pass adds
nothing back. The test asks the module's own source, because both write sites need a tokenizer and
a store to reach and what must never return is the assignment itself.

## 3. Fetch the episode lists we never asked for

**THE RULING, given by the project owner 2026-08-13:** the category of works living only in the
release feed should essentially not exist by construction. A new work from a platform we already
know about, arriving by an attesting route, presumptively gets its own work page.

**THIS SECTION WAS WRITTEN WRONG AND THE OWNER CORRECTED IT THE SAME DAY.** It argued that 47 of
these works reach us through a route that states no chapters, and recommended a row shape that could
carry a chapter count of zero. The question that undid it was whether ニコニコ really says so little,
and it does not: 見える子ちゃん has a full episode list on its page, free at the start and the end
with the middle behind the app. We had simply never fetched it.

The adapter already exists and already names this problem. `adapters/nicovideo/works.py` writes
`web_work_chapters` from the same page `releases.py` reads for dates, and its docstring says why:

    WHY THIS SITS BESIDE releases.py. `releases.py` writes `work_update_dates`: the platform said
    this work updated on this day ... That record type produces no row in the works list, so a
    serialisation reachable only here was invisible as a work however often it updated.

It even models the case the owner described. `partial` is asked of each page rather than asserted of
the platform, so a run whose middle is app-only reports a highest position above the number of items
rendered and says the page left some out.

**WHAT IS ACTUALLY WRONG IS THE WORKLIST.** The adapter runs from
`data/queue/serialisation-joins.yaml`, which holds 674 ニコニコ entries and every one of them is a
work already joined to a printed record, carrying a `w`-id and a MADB code. A work found by the
discovery sweep has no print record to be joined from, so it never enters the queue and its episode
list is never requested. 337 works have their episode list held; 見える子ちゃん is not among them.

So the fault is a capture gap wearing the shape of a modelling problem, and the fix is to ask.

| route | works it names | with no work page |
|---|---|---|
| `web_work_chapters` | 1,522 | 170, held out by rules that are about something else |
| `work_update_dates`, ニコニコ漫画 | 486 | 76 |
| `web_series`, publisher yuri labelling | 165 | 13 |
| `web_releases`, GigaViewer Atom | 30 | 6 |

53 works are attested on a platform we already read and hold no chapter-level record anywhere. They
include `わたしが恋人になれるわけないじゃん、ムリムリ！（※ムリじゃなかった!?）`,
`おちこぼれフルーツタルト` and `見える子ちゃん`, which are not obscure. A reader meets each of them
on the releases page, follows nothing, and the work is absent from every list the site draws.

**WHAT TO DO.** Feed the discovery candidates into the worklist the chapter-level adapters already
read, rather than gating that worklist on a print join. GigaViewer writes `web_work_chapters` too,
from `*-series-feeds.yaml` and `comic-days-confirmed.yaml`, so the same move covers its six.

**THE CODE IS DONE AND THE DATA IS NOT PUBLISHED, 2026-08-13.** `works.py --ids` now takes several files, and the one
that closes the gap is `data/source/nicovideo/nicovideo.yaml`, which is what `releases.py` writes
about every work it saw. Both adapters read the same page, one for its dates and one for its
episodes, so a work whose update this project recorded is a work whose episode list it can ask for.
The coverage yardstick was tried first and reached only part of it: a sample of eight pages, which
left 36 works behind and made the point that a worklist has to be the population rather than a
sample of it.

337 targets became 492, the fetch returned 10,530 rendered episodes against 8,336, and the corpus
went from 1,395 works to 1,436. The §3 population fell from 53 to 6, and the ニコニコ part of it to
0. `works without English` stayed at 0 through 41 new works arriving, which is §1 doing the job it
was built for.

Two shapes had to be handled on the way. `targets` read one key of one document, and the documents
name their entries `joins`, `works_missing` and `works`. And the same word is a count in one file
and a list in another: `webcomics-gap.yaml` writes `listings: 400` and `serialisation-joins.yaml`
writes `works: 547`, each summarising what the document holds, so the reader asks whether a value
is a list before iterating it.

**THE RUN WAS THEN WITHDRAWN, AND WHY MATTERS MORE THAN THE NUMBERS.** Admitting the 41 works
fails `content flags are accounted for`, an invariant: 田舎エッチ ～田舎のエッチな女の子と過ごすひと夏
の… arrives content-flagged and appears in no `withheld.yaml`. That register records a WITHHOLDING
decision about adult content, which is the project owner's and not a build's, so the fetched
`data/source/nicovideo/works.yaml` was reverted rather than the gate satisfied. The adapter, its
test and the stage-a wiring all stay, so the next update run brings the works in the moment the
ruling exists.

Eleven budgets rise with those works and each wants reading rather than a blanket acceptance.
`credit fields an identifier does not cover` goes 28 to 51 and `renderings with nothing to show`
18 to 25, both because 41 works bring credits nobody has resolved. That is the real size of §3 and
it was invisible until the fetch ran.

**WHAT THE 24 DUPLICATE PAIRS TURNED OUT TO BE, measured rather than guessed.** `one work under two
names in a list` goes 3 to 27, and they are not romanisation collisions as the budget's key allows
for. Most are IDENTICAL titles: `私を喰べたい、ひとでなし` beside itself, `田所さん` beside itself.
They are works the corpus already holds, arriving again from ニコニコ under an identifier of their
own because nothing joined the new row to the held work.

`adapters/serialisation/promote.py` rules on this exact case: where the serialisation is already in
the corpus under an identifier of its own it is a MERGE done by hand with `--merge`, because
retiring an address that has been published is not something a pass does in bulk (RUNBOOK §11).

**DONE 2026-08-13, on the project owner's authority to merge.** `--attach` was tried first, since
the discovery case retires nothing, and the registry refused all but one of them with the reason
that settles it: the addresses already held identifiers of their own, which is the merge case
exactly. 22 merges and 1 attachment later, `one work under two names in a list` is back to 3, its
value before any of this.

The refusal is worth keeping in view. `--attach` says it "refuses an anchor another work holds,
because that would be a merge", and that guard is what told me which operation this was; guessing
would have produced 22 wrong joins.

One consequence was not foreseen. Merging changed which spelling a surviving work carries:
`Qyootie Q! ―麒麟娘と婚約事情―` became `Qyootie Q! -麒麟娘と婚約事情-`, the way ニコニコ writes it, and
the curated English was keyed on the em-dash form, so it named a work nothing held. `test_curate`
caught it. The entry is re-keyed with a note; a merge can move a title and anything keyed on the
old spelling goes with it.

**THE SIX GIGAVIEWER WORKS ARE NOT DONE.** `series_feeds.py` runs for ichicomi alone, because only
platforms declaring `series_pages` do work without `--candidates`, so reaching コミックゼノン and
サンデーうぇぶり this way needs that registry extended rather than a worklist widened.

**WHAT TO CHECK BEFORE BELIEVING IT IS DONE.** Some of these works may genuinely render no readable
episode, which is the case `build.py` already refuses as a route no browser can read. That refusal
is correct and it is a different outcome from never having asked. The two have to be told apart, so
a work whose page was fetched and offered nothing should be recorded as asked and declined rather
than left looking untried.

Three consequences to expect. `works without English` leaves zero unless §1 has run, because 48 of
these works have no English in the store for exactly the reason §1 names. Admission has to go
through identity rather than making a work per title, since 3 of them are edition variants of works
already held, in the shapes `（Lilie comics）` and `【連載版】`. And the dormancy invariant starts
applying to them, so some land as slow or dormant on arrival.

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

The base title has to be matched through something that equates a kana spelling with its kanji one,
which is what these three need and nothing else in the corpus currently asks for. Then the 4 whose
base work is absent are the only open question, and it is a small one: whether a translated edition
may be the only record of a work we hold no Japanese record for.

**THE COUNTER-CASE TO TEST.** A product whose base title matches a DIFFERENT work by the same
circle. The join is on a title inside a title and a doujinshi circle publishes many, so a match that
skips the creator would merge two works by あとき into one.

**THE MATCHER IS DONE, 2026-08-13, and the reading is what carries it.** No fold could do this:
`namekey.fold` is the identity key and is strict on purpose, `loosely` adds case, brackets and a
catalogue's name separator, and none of them reaches a kanji spelling and its kana one. Both forms
read `ハズカシガリ ヤ ノ レイムサン` and `pass4_analyser` says so for either, so `facts/edition`
compares readings rather than spellings and requires the creator to agree, which is the test
`ndl_volumes` already applies for the same reason.

Run against every BOOK☆WALKER record it resolves 3 and refuses 4, which is right on both sides: the
three are the kana/kanji cases and the four name a base title the corpus does not hold, so there is
no second end to join to.

**THE MERGE IS DONE, 2026-08-13, and the worry about it was unfounded.** Retiring an id was named
here as the reason to wait, and the registry has carried the answer all along: a merged entry keeps
`merged_into` and stays resolvable, `identity.py` says so at the top of the file, and 128 entries
already do it. One of them, `転生王女と天才令嬢の魔法革命 【タテスク】`, is a vertical-scroll EDITION
merged into its serialisation, which is this case exactly.

`w01932` and `w01577` now carry `merged_into: w02056` with the argument beside them, so `w02056`
holds all five records: the Japanese original, and its Chinese, English, Korean and Spanish
editions. The 4 whose base work the corpus does not hold are untouched and stay §4's open
question.

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

§5a was done 2026-08-13. `credits.people_only` asks each credit in a field, and not the field.
Every refusal `is_a_person` makes anchors at the start of a string, so a field opening with a real
name passed whatever followed it, and `ONE_SHOT_LABEL` had been written for this exact string and
was being asked the wrong question. It also rescues a name the old rule discarded: `金子ある / #1(1)`
failed as a whole and the capture dropped the field entire, losing a real person to keep out a
chapter number. The two rows already on disk heal on the next Stage C run, since a source record is
stored as fetched and never hand-edited.

**§5b DONE 2026-08-13.** きら星ポータル titles its page `作品 / 誌名 - サイト`, with no `|` for the
title rule to anchor on, and says `著者：深水たろー` in the body inside an anchor to its own author
page. `LABELLED_CREDIT` reads a credit the page LABELS, which is better evidence than a position in
a title: it says which field this is rather than leaving it to be inferred. The label vouches for
nothing, so what follows it still goes through `people_only` and a one-shot title sitting where a
name belongs is refused exactly as it is in a page title.

**HOW BOTH ARE PROVED.** `incomplete attested rows` already counts a release missing a chapter name,
an author or an access state, and stood at 37 on 2026-08-13. Neither of these fault classes moves it,
since one row has an author that is wrong rather than absent and the other is counted already.
A count of credits holding a chapter marker would see the first.

## 6. Ask the shops about a work, rather than waiting for their yuri shelf to name it

**FOUND BY THE PROJECT OWNER 2026-08-13**, on the same work as §3: 見える子ちゃん has print editions
on コミックシーモア and on BOOK☆WALKER, and the corpus holds a record from neither.

**EVERY SHOP ROUTE IS SHELF-DRIVEN.** `adapters/recon/bookwalker_shelf.py` opens with what it is:
"BOOK☆WALKER's 百合 shelf, read as a candidate list". So the question the pipeline asks a shop is
`which works do you file under 百合`, and it never asks `do you sell this work`. A shop that stocks
a book and files it elsewhere is indistinguishable from a shop that does not stock it.

**THE CORPUS ALREADY KNOWS THIS WORK IS IN SCOPE**, from a different comparator.
`data/coverage/webcomics-gap.yaml` lists it under Web漫画アンテナ's 百合 tag with
`["女子高生", "オカルト", "ホラー", "幽霊", "百合"]`, and that file exists to be the work queue for
every listed update eventually appearing in our feed. So one comparator files it as yuri, the
shops file it as horror, and nothing carries the first judgement across to the second.

**HOW BIG IT MIGHT BE.** 560 of the 1,349 rows holding a web serialisation hold no print record at
all. That is the population to ask about rather than the size of the gap, since a web serial with no
book is an ordinary thing and many of those 560 will be exactly that. What makes it worth asking is
that the cost per work is one search on a shop we already read, and the answer is a volume list with
ISBNs and dates, which is what VOLUMES-PLAN spent two sections trying to reach by other means.

**WHAT TO DO.** Take a work the corpus already admits and look it up by title on the shops, the way
§6 of VOLUMES-PLAN asks the National Diet Library by title. The admission is already made and the
shop is being asked about stock rather than about genre, so nothing here launders a retailer's
shelving into a classification, which is the line `bookwalker_shelf.py` draws and this must not
cross.

**THE COUNTER-CASE TO TEST.** A title search on a shop returns the wrong book, which is exactly why
the NDL pass refuses to accept a record without agreeing on the author. The same guard applies here
and for the same reason.

## What is already in hand

The National Diet Library run from VOLUMES-PLAN §6 is still going, at 1,512 works asked of about
1,541 and 397 answered. §6 item 4 and §7 pick up from its output and are unaffected by anything
here.
