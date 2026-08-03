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

## The series this document was asked to find

The brief asked for a well known, ongoing, explicitly GL series carried in a print magazine that
puts none of it online, not even late. That is a narrow claim, and every strong candidate checked
against it failed the check: フォワード's flagship yuri title turned out to be on COMIC FUZ,
MURCIÉLAGO turned out to be on four digital storefronts, ハルタ and アライブ both feed platforms
already watched, and the two most promising leads out of our own print corpus turned out to be
sitting on ichicomi the whole time, missed only by a gap in `series.json`'s own coverage. The one
confirmed case of a magazine putting none of its content online, ガレット, is not commercial and not
what "well known" describes.

So the honest state of this question, after checking every candidate this research turned up, is
that no commercial, well known, ongoing, explicitly GL series was confirmed to be entirely absent
from the web. Several plausible candidates were checked specifically and eliminated with evidence,
which narrows where a second pass should look and says more than an unchecked list would have. 秋田書店's and 小学館's magazines were checked
shallowly and are the most likely place a real example is still sitting, precisely because no
platform for either publisher is in `data/platforms.yaml` yet and neither was searched past a first
pass. A publisher whose web presence has not been mapped at all is a better place to keep looking
than one, like 芳文社, whose web presence is well documented and turned out to cover the case being
searched for.

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
