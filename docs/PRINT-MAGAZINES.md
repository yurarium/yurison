# Print magazines: what carries yuri, and what the pipeline cannot see

Research note, 2026-08-03. Scoped to the question of which Japanese print manga magazines carry
yuri or GL content, what is knowable about their back issues and forthcoming schedules, and which
of their series never reach a web platform at all. Written for whoever next decides whether print
magazines are worth building against, not as a data dump.

## The corpus is blind by construction

`data/build/works.json` holds 302 print works. All 302 carry the same imprint family: 一迅社's ID
Comics / Yuri-Hime line, enumerated out of MADB by matching `schema:brand` against that imprint's
name variants ([MADB](MADB.md)). Every one of them is コミック百合姫's own tankobon output. A
publisher field that reads 講談社 on some records names a distributor for those same books, not a
second publisher; see MADB for the 頒布/発売 split.

This means the print holdings are not a sample of the Japanese yuri magazine field. They are one
publisher's output, captured because that publisher's imprint happened to be identifiable in bulk
data. Anything serialised in 月刊コミック電撃大王, the まんがタイムきらら magazines, ハルタ, 楽園,
月刊アクション, or any of the other magazines below is absent from `works.json` entirely, not
undercounted. A reader of the rest of this document should hold that fact before judging anything
in it: the print side of this project currently sees one imprint out of a real field of a dozen or
more.

Widening the enumeration is possible in principle and has not been attempted. MADB's `metadata101`
carries `schema:brand` for every 単行本 it holds, and the imprint-matching method that built the
302-work corpus is not specific to コミック百合姫. Anyone repeating it needs the imprint name first:
「まんがタイムKRコミックス」for the まんがタイムきらら lineup, 「楽園コミックス」for 楽園's now-closed
run, and so on, worked out from the outward search below rather than from MADB itself, because MADB
has no genre field to search by. That ordering, magazine first and imprint second, is why this
document runs magazine-outward rather than corpus-outward: a check against `works.json` and
`series.json` was tried first and produced false leads, recorded further down, because both files
describe the same single imprint.

The blindness holds on a concrete case. 加瀬さん, the series at the centre of this document's central
finding below, its author 高嶋ひろみ, its magazine ウィングス, and its publisher 新書館 return zero
matches each against every file under `data/`, checked directly with `grep -rl` rather than taken on
report. This is a series licensed into English by Seven Seas and about as well known as the genre
gets, and the corpus holds zero occurrences of its own title string. That is what "one imprint out of
a dozen or more" means in practice, on the single case where it is easiest to see.

The 302 figure carries a second softness, this one inside the imprint the corpus does hold, and it
runs the other way: a single title claimed by more than one work id. Grouping every work in
`works.json` by its exact Japanese title turns up five such pairs: ゆるゆり, citrus, Girls Love,
くちびるに透けたオレンジ, and キミイロ少女. ゆるゆり's split, 26 volumes against 12 under two MADB
series records, is already named as a known duplicate in [MADB](MADB.md), left for a curation
decision rather than fixed at the adapter. citrus is a second confirmed case, and the first pass at
explaining it here was wrong and is corrected rather than quietly dropped: reading C357075's six
volumes and C360560's four as an original run plus a completing reissue assumed the four-volume
group continued the story where the six left off. The dates rule that out. All four of C360560's
volumes, ISBNs 9784758074483, 9784758074520, 9784758074537 and 9784758074544, are dated the same
month, MADB's 2015-08, which is not what a series continuing volume by volume looks like. Checked
against 一迅社's own catalogue rather than left as a guess: ISBN 9784758074520 is listed there as
citrus (1) 新装版, and ISBN 9784758074483 as citrus (4) 新装版, each a standalone B6 paperback at
¥748, both dated July 18, 2015 by the publisher
([一迅社WEB, citrus (1)](https://data.ichijinsha.co.jp/detail/75807452);
[一迅社WEB, citrus (4)](https://data.ichijinsha.co.jp/detail/75807448)). So C360560 is not a boxed
set either: it is four individually catalogued 新装版 volumes, a reissue of the first four volumes
under new ISBNs, published together as one batch. Where that leaves C357075 is not fully settled. It
holds the original, pre-reissue printings of volumes 1, 2 and 3, plus the later volumes 5, 9 and 10;
volumes 4, 6, 7 and 8 do not appear under either citrus work id anywhere in `works.json`, and why is
not established here. What is established is the shape MADB and the extractor together produce:
`metadata104` carries the original series and the 新装版 batch as two distinct 単行本シリーズ records,
`adapters/madb/extract.py` groups strictly by that id, and a repackaging of already-published volumes
comes out the other end looking like a second work rather than like an edition of the first. The
other two pairs, くちびるに透けたオレンジ (2010 and 2015, the same five-year gap) and キミイロ少女
(2014 and 2018), match that shape closely enough to read as the same mechanism, though neither was
checked against a primary source the way citrus was. So of 302 works, at least two pairs are
confirmed duplicates of one story and two more are suspected on the same evidence shape, before any
question of what a print-only magazine adds. The number is real but softer than it looks, in both
directions: some titles it should hold are entirely absent, and at least a few it does hold are
counted more than once, or, on the evidence of citrus's missing middle volumes, possibly undercounted
and overcounted in the same work.

## コミック百合姫: the one magazine already covered

Publisher 一迅社. On sale the 18th of each month, ¥920, print and a same-day digital edition
([Wikipedia](https://ja.wikipedia.org/wiki/%E3%82%B3%E3%83%9F%E3%83%83%E3%82%AF%E7%99%BE%E5%90%88%E5%A7%AB)).
Founded July 2005 as a special issue of 月刊コミックZERO-SUM, succeeding the defunct 百合姉妹, and
independent from its January 2008 issue. A web edition, ニコニコ百合姫, launched February 2013 and
has since become 一迅プラス (ichicomi.com), the platform this project already watches under the id
`ichicomi`.

Back issues are addressable. Fujisan.co.jp lists 160 issues for sale going back to 2009, ¥920 each,
paper only through that particular retailer
([Fujisan](https://www.fujisan.co.jp/product/1281683839/b/list/)); digital back numbers are sold
separately through BOOK☆WALKER and comparable stores. Ichijinsha's own site carries a back-number
archive at `ichijinsha.co.jp/yurihime/backnumber/`. Forthcoming issues are knowable exactly one
month out, which is what a fixed on-sale day gives you: no announced schedule extends further, and
new-series announcements arrive with the preceding issue rather than ahead of a season the way an
anime programming block does.

Whether コミック百合姫's own serialisations reach ichicomi turned out to be harder to answer from
`series.json` than expected, and the answer is a finding about our own tracking rather than about
the magazine. 302 works in `works.json` were compared against the 986 titles in `series.json` by
normalised title (`adapters/textnorm.py`); 230 have no match. The two most recently active,
無力聖女と無能王女 (volume 2, 2026-01) and 春の光に呑まれても (volume 1, 2026-03), read as the
strongest print-only candidates the data could offer: both had reached tankobon in 2026 with no
corresponding web title. Checking ichicomi's own コミック百合姫 series index directly
(`ichicomi.com/series/yurihime`) found both present, one serialising and one archived as complete.
Neither is print-only. `series.json`'s coverage of ichicomi itself has a gap that the title-diff
method cannot distinguish from a genuine absence, which is exactly why the method should not be
trusted for this question without a live check on every candidate it produces, and why it is
recorded here rather than relied on.

## The rest of the commercial field

**つぼみ**, 芳文社. An anthology-format yuri tankobon line rather than a newsstand magazine in the
コミック百合姫 sense, running 2009 to its 2016 discontinuation
([Wikipedia](https://ja.wikipedia.org/wiki/%E3%81%A4%E3%81%BC%E3%81%BF_(%E3%82%A2%E3%83%B3%E3%82%BD%E3%83%AD%E3%82%B8%E3%83%BC))).
Ceased, so no forthcoming schedule to establish. MADB holds a record for it (C123168) but zero
issues in cm102, so bulk data cannot supply a back-issue list either; that gap is recorded in MADB.

**百合姉妹**, サン出版, 2003 to 2004, コミック百合姫's direct predecessor after its own
discontinuation. Absent from MADB entirely, checked there against all 35 サン出版 magazine records
([MADB](MADB.md)), so nothing in bulk data can stand in for a publisher source on this one.

**楽園 Le Paradis**, 白泉社. Not a yuri specialist: a triannual (February, June, October)
all-original anthology spanning several romance genres, yuri and GL among them, running every story
as a first-print commission rather than a serial chapter
([Wikipedia](https://ja.wikipedia.org/wiki/%E6%A5%BD%E5%9C%92_Le_Paradis)). Its 50th and final issue
went on sale February 2026, ending a sixteen-year run
([Comic Natalie](https://natalie.mu/comic/news/646367)). Collected as 楽園コミックス. Because every
story in it is new to that issue rather than an ongoing series, "back issue" and "forthcoming
schedule" both collapse into the same fact: it is finished, no further issues exist, and the fifty
issues already published are the entire back catalogue. Whether any of its yuri content reached the
web was not established either way in the time available; Hakusensha runs a store at
hakusensha-e.net that sells the anthology issues themselves as ebooks, which answers "is the volume
purchasable digitally" without answering "did any individual story appear as a freestanding web
chapter."

**まんがタイムきらら family**, 芳文社: きらら (9th), MAX (19th), フォワード (24th), キャラット (28th),
each a monthly on-sale day
([Wikipedia](https://ja.wikipedia.org/wiki/%E3%81%BE%E3%82%93%E3%81%8C%E3%82%BF%E3%82%A4%E3%83%A0%E3%81%8D%E3%82%89%E3%82%89)).
Since July 2021 the flagship three run a catch-up serialisation on ニコニコ静画's きららベース channel,
posting chapters some time after the print issue, which is exactly the delayed-and-therefore-less-
interesting case rather than the one this document is chasing. フォワード is named as excluded from
that program in the same source. A community thread on ニコニコ大百科 about 星屑テレパス, フォワード's
best-known yuri title (ongoing, seven volumes planned, an anime and a live-action drama both made),
describes its きららベース posting as having stalled partway through, before a later story arc, well
short of the current print chapter; that specific claim rests on a single community source and was
not independently confirmed, so it is recorded as a lead rather than a fact. What was confirmed
directly: Houbunsha's own app, COMIC FUZ, carries individual フォワード series with dated free
chapters regardless of the きららベース exclusion. betock's 色んな女の子とキスをしていたら、百合キス
に目覚めてしまいました…。, an explicitly-titled and currently-running GL comedy from フォワード, has
its ninth episode posted free on COMIC FUZ
([X, まんがタイムきらら編集部](https://x.com/mangatimekirara/status/1634569876672245760);
[comic-fuz.com/manga/2973](https://comic-fuz.com/manga/2973)). COMIC FUZ is already in
`data/platforms.yaml` as `comic-fuz`, watched. フォワード's exclusion from one Houbunsha channel does
not mean its series are absent from the web; it means they are absent from a specific channel we
were not otherwise going to check, and checking the obvious candidate ruled it out.

**ヤングガンガン**, スクウェア・エニックス, twice monthly (first and third Friday). Home of
MURCIÉLAGO, a long-running action series that 百合ナビ itself categorises as yuri
([百合ナビ](https://yurinavi.com/2026/07/05/murcielago-animeka/)) and that is getting a 2026 anime.
Checked and ruled out as a print-only case: individual chapters are sold and partly free-readable
across LINEマンガ (three free), ebookjapan, めちゃコミック and コミックシーモア, and ガンガンONLINE
carries ヤングガンガン material as well. Whatever the case for or against calling MURCIÉLAGO
"explicitly" GL rather than yuri-adjacent, it is not print-only either way.

**ハルタ**, KADOKAWA, ten issues a year, mid-month except January and July. Its output already
reaches the web through comic-walker.com/label/harta, which is the ComicWalker property behind the
`kadokomi` platform this project already watches. No specific yuri title in ハルタ was identified and
checked in the time available, so this is a magazine-level finding rather than a series-level one:
whatever it carries has a route online, unlike フォワード or 楽園.

**月刊コミックアライブ**, KADOKAWA, 27th of the month. KADOKAWA operates 百合倶楽部, a
yuri-only section of ComicWalker built for its fourth anniversary specifically to aggregate yuri
manga across its magazines
([KADOKAWA](https://www.kadokawa.co.jp/topics/1801/)), which is a publisher stating outright that it
puts its yuri content online rather than holding any of it back. No further series-level check was
made.

**ヤングチャンピオン / チャンピオンRED / ヤングチャンピオン烈**, 秋田書店. チャンピオンクロス
(`championcross`) is already watched. No currently-running series in these three that reads as
explicitly GL was identified in the time available; two 2026 new serialisations turned up in
searches and neither is GL. Recorded as not established rather than as absent, since the check was
shallow.

**月刊flowers**, 小学館. Historically the venue for 青い花, long completed. Nothing currently running
there was identified as explicitly GL in the time available. Also not established.

**ガレット**, self-published, unaffiliated with a commercial publisher. Issue 38 went on sale June
2026 on a roughly bimonthly to quarterly pattern, sold through its own site and at events
([galetteweb.com](https://galetteweb.com/)). This is the cleanest print-only case found: the site is
an announcement and mail-order page, not a reading venue, and nothing points to any of its content
being posted as web chapters anywhere. It is also not what "well known" ordinarily means for a
manga magazine: it is a doujin-adjacent yuri anthology zine with a small, dedicated readership, not
a newsstand title. Absent from MADB entirely, per the earlier finding in [MADB](MADB.md).

## ウィングス and 加瀬さん: the series this document was asked to find

Every candidate reached by working outward from the magazines this project already half-knows about
failed the print-only test on direct check, recorded above. The one that holds up came from outside
that set entirely, named directly rather than surfaced by any method here: 加瀬さん, by 高嶋ひろみ,
currently serialising as 山田と加瀬さん。in ウィングス, published by 新書館.

**新書館** is a shōjo and BL-adjacent publisher whose best-known property is ウィングス itself,
running continuously since 1982. The magazine ran monthly from its tenth issue through September
2009 under the title 月刊ウィングス, then reverted to its original bimonthly pattern, on sale the
28th of even-numbered months
([Wikipedia](https://ja.wikipedia.org/wiki/%E3%82%A6%E3%82%A3%E3%83%B3%E3%82%B0%E3%82%B9_(%E9%9B%91%E8%AA%8C))).
That pattern held through 2026: the June 2026 issue is dated on sale April 28, 2026, and Fujisan's
listing carries 高嶋ひろみ among that issue's credited authors
([Fujisan](https://www.fujisan.co.jp/product/160/new/);
[ebookjapan](https://ebookjapan.yahoo.co.jp/books/322301/A006758047/)). Back issues are addressable:
Fujisan lists 96 back numbers, paper only through that retailer, filterable back to 2010
([Fujisan](https://www.fujisan.co.jp/product/160/b/list/)). A forthcoming issue is knowable exactly
one publication cycle ahead, the same shape as コミック百合姫's monthly pattern stretched to two
months, and no further than that from any source checked.

新書館 does run a web presence for the Wings family, at `shinshokan.com/webwings/`, distinct from its
separate web-novel site `nwings`. What that site does today is show a sample read and purchase links
into 新書館ビューワー and Yahoo!ブックストア for each title, 山田と加瀬さん among them, rather than
post full chapters for free reading the way ichicomi or comic-walker do
([shinshokan.com/webwings/title43.html](https://www.shinshokan.com/webwings/title43.html)). That was
not always true of this specific series. Per Wikipedia, ひらり、, the anthology 加瀬さん started in,
was discontinued in 2014, and the series moved into an actual web serialisation under the name
ウェブマガジンウィングス that ran until March 2017, then into the print ウィングス magazine from its
April 2017 issue onward
([Wikipedia](https://ja.wikipedia.org/wiki/%E5%8A%A0%E7%80%AC%E3%81%95%E3%82%93%E3%82%B7%E3%83%AA%E3%83%BC%E3%82%BA)).
So the claim as given, that the magazine puts none of it online, is accurate for the current
serialisation and not accurate as a claim about the work's whole history: it spent roughly two and a
half years as a web-first series before returning to print, and it is the print return, not an
absence of any web episode ever, that has held for the nine years since. Worth stating precisely
rather than rounding off, because the distinction is exactly the kind this document exists to keep.

加瀬さん also renames itself between volumes, and the actual sequence, checked against Wikipedia and
cross-read against BookWalker's and Manga Zenkan's listings rather than taken from any single
description of it, runs あさがおと加瀬さん。(2012), おべんとうと加瀬さん。(2014), ショートケーキと
加瀬さん。(2015), エプロンと加瀬さん。(2017), さくらと加瀬さん。(2018), then 山田と加瀬さん。1 through
5 (2019 to 2025), ten volumes under six titles, one continuous story throughout. This project keys a
work on its title and folds presentation with `adapters/textnorm.py`, correctly, since two different
words are two different works there. A series that changes its title every volume or two defeats
that keying by design rather than by bug: MADB's imprint enumeration, run against this series, would
return several one- or five-volume works joined by nothing, because title-matching is exactly the
mechanism that cannot see past a deliberate rename. The proportionate answer to one known case is not
a new mechanism; it is the same hand-reviewed entry this project already uses for facts a machine
cannot derive, the kind `data/names/curated.yaml` holds with a basis, a source and a note. That file
is being worked on elsewhere as this document is written, so the entry is not made here, but the
shape worth recognising if a second case turns up is this: several single-volume works, one author,
one imprint, titles that share a distinctive element and differ only in what precedes it. The owner
could not name a second instance of a renaming series specifically, and this document did not go
looking for one; it may be a unicorn, and is recorded as one rather than generalised into a problem
it has not been shown to be.

citrus, above, is the same failure from the other side and is already sitting in data this project
holds rather than in a magazine it does not watch: one title, two work ids, instead of one series
under six titles. The two are worth naming together because they are the same mechanism read in
opposite directions, title-keying that cannot see past a change on one side and cannot see past a
sameness that hides a real difference on the other, and because between them they show the failure
is not confined to whatever gets built to reach ウィングス. citrus+, the sequel, does not have this
problem: its print title `Citrus +` and its web title on ichicomi, `citrus+`, fold to the identical
string under `adapters/textnorm.py` (`norm("Citrus +") == norm("citrus+")`, checked directly), so
print and web already agree there and only the base series is fragmented. One more instance of the
same underlying class turned up while checking this, worth a sentence rather than a section: three
source-layer titles store a voiced kana as a decomposed pair, base character plus a combining sound
mark, rather than as the single composed character. 銀玉の価値を上げる方法 in
`kuragebunch-series-feeds.yaml` carries one in 上げる, さよならミュージアム in
`tonarinoyj-series-feeds.yaml` carries one in ジ, and the subtitle of お姉さまと巨人 ～お嬢さまが異世界
転生～ in `kadokomi/chapters.yaml` carries one in が, each confirmed directly by inspecting the stored
bytes rather than assumed from the visible glyph. `textnorm.py` applies NFKC, which composes them, so
nothing downstream breaks, but a person comparing raw titles by eye or with a plain string match would
see two different spellings of one name and miss the match, the identical shape as citrus and 加瀬さん
one level down, in the encoding rather than in the title.

Whether ウィングス carries any other yuri or GL content was not chased, on purpose. The magazine is a
general shōjo and boys'-love-adjacent anthology title with dozens of series across genres in any
given issue; 加瀬さん may be the only one that reads as explicitly GL, and padding this section with
a search for a second title to make the case broader would manufacture a pattern the evidence does
not support. One well known, ongoing, explicitly GL series that a magazine keeps off the web is a
complete finding on its own and does not need a second series to justify writing it down.

That also sets the shape of what this argues for building. A magazine carrying a field's worth of
yuri is a case for coverage at the magazine level, the way コミック百合姫 or a Kirara title would be.
A magazine carrying one such series is a case for something narrower: a way to hold a named work that
no watched platform will ever feed, entered once on the strength of the work rather than of its
carrier. Those are different features. Nothing here argues for the first on ウィングス's account, and
building the second only for this one series would be reasonable exactly because it is this
well known.

One more consequence follows directly. A print-only work can carry volumes and a first-publication
date; it cannot carry an update, because nothing produces one. It belongs on the works-and-volumes
side of whatever interface reads this corpus, never in an update feed, and a build that tried to
place it there would be describing a fact about the pipeline's reach rather than a fact about the
work. That is the difference between a gap in tracking, which this document is largely about, and a
work that is simply not the kind of thing an update feed describes.

秋田書店's and 小学館's magazines were checked shallowly earlier in this document and nothing was
confirmed either way there; nothing found for 新書館 changes that, since 新書館 was not on that list at
all before the owner named it directly. The method this document used to build its magazine list,
working outward from platforms and magazines already somewhere in this project's orbit, missed 新書館
entirely, and no search run against that list would have reached it. That is worth carrying forward
more than any single magazine profile above: the field is larger than what a search seeded from our
own data will find, and the one confirmed case came from someone who already knew the genre rather
than from the method.

## Whether MADB's issue data could carry this

MADB's magazine-contents relation, `metadata108`, holds zero records for the コミック百合姫 line and
for つぼみ ([MADB](MADB.md)). That finding is not in question here: it was reached by direct query
against the release data, and nothing found in this research contradicts it. Issue contents on major
mainstream titles (週刊少年サンデー, 週刊少年ジャンプ and similar) are well covered, at up to a few
thousand issues each, which is the opposite shape from what a back-issue or forthcoming-schedule
feature for the yuri field would need. A feature built on `metadata108` would work well for magazines
this project has no reason to track and not at all for the ones it does.

What MADB is good for here is the imprint enumeration, and that only helps once a magazine's
tankobon imprint name is already known from a source outside MADB, because MADB carries no genre or
subject field to search by. The corpus could be widened publisher by publisher, following the same
`schema:brand` match used for コミック百合姫, but the research has to run outward from magazines
identified elsewhere first. MADB cannot be the starting point for this question; it can only confirm
and enumerate what a publisher source already pointed at.
