# Remaining gaps and the path through each

> **The counts in this document are not maintained by hand.** Numbers that can be derived are
> derived — see `data/build/run.json` and the technical view at `kari/status.html`, which are
> regenerated on every build. A gap list edited by hand goes stale, and this one did: several
> entries below were closed before anyone updated them.
>
> What belongs here is the part that cannot be computed — **why** a gap exists and what the route
> through it is. Keep that; take the arithmetic from the build.

State as of 2026-08-01, after onboarding ニコニコ漫画. Written to be acted on, so each entry says
what the gap actually is, what the route through it costs, and what would make it worth doing.

Acceptance against both Tier C yardsticks now stands at 100% on watched platforms (202/202 against
Web漫画アンテナ excluding two deliberate 試し読み exclusions, 70/70 against 百合ナビ), across 705
releases and 316 works. Coverage is no longer the constraint. What follows mostly is not about
coverage.

---

## 1. Classification — the only gap that matters

**302 works, none with a `content_tier`.** Every work carries a `marketing_label`; not one carries
the interpretive axis. The two-axis scheme in [DEFINITIONS §3](DEFINITIONS.md) is currently
one-axis in practice.

This cannot be automated, and the temptation to try should be named so it can be refused: a
publisher's 百合 tag is `marketing_label` *by definition*, an aggregator's tag is a third party's
opinion, and "serialised in 百合姫" is the venue's identity rather than the work's. Deriving
`content_tier` from any of them would collapse the two axes into one and destroy the thing the
scheme exists to preserve.

**Path.** `adapters/classify/queue.py` builds `data/queue/classification.yaml`: every unclassified
work with its imprint, creator, volume count, first publication, and whatever platform and
aggregator tags we hold, plus an empty `content_tier` and a `basis` skeleton. Filling a row and
moving it to `data/overlay/<work_id>.yaml` classifies the work — the build already prefers overlay
over every source.

Ordered weakest-evidence-first, longest series first within each band, because that is where a
human adds most:

| Corroboration beyond the imprint | Works |
|---|---|
| none | 220 |
| one source | 48 |
| two sources | 34 |

**Cost.** Human, per work, and irreducible. But the queue is the difference between 302 blank
fields and 302 questions with the evidence already attached.

---

## 2. pixivコミック — reachable, deliberately not taken

Previously recorded as closed by operator choice. That was half right. The API at
`/api/app/works/...` returns 403 to a self-identifying non-browser request, and spoofing the client
to get past it is out under §5. But the site renders fine in an actual browser, and a browser is
the client the operator serves — no access control is circumvented by using one.

Confirmed 2026-08-01 by rendering `comic.pixiv.net/works/12066`: title, author, the publisher's own
百合 tag, per-episode availability (`掲載期間が終了しました` vs readable), and `更新日` at work
level. Everything needed is there.

**Path.** A rendering step in the pipeline, one page per work, ~131 works.

**Why not now.** Overlap 0.77 — the highest of any platform, meaning almost everything it lists is
available elsewhere too, usually at better image quality. Onboarding origin platforms erodes its
exclusive count without touching it, twice demonstrated. Adding a headless browser to the pipeline
is the largest single increase in operational complexity available, in exchange for the smallest
unique contribution of any large target.

**Trigger to revisit.** Re-measure its exclusive count now that ニコニコ is watched. If it stays
above ~40 works after that, the browser step earns its keep.

---

## 3. Platform coverage — worked to the series, not the platform

Every platform in the survey has a route or a stated reason, and so does every individual series.
The count that matters is the second one: a platform can be "watched" while particular works on it
are never fetched, which is what was happening.

**Series a comparator reports that we hold no chapter data for: 10** (from 65).

| Why | Count |
|---|---|
| withdrawn at source — 掲載期間 ended, publisher serves an empty feed | 3 |
| not yet diagnosed further | 3 |
| route identified, work outstanding | 2 |
| platform publishes no per-chapter dates | 1 |
| geoblocked | 1 |

Named individually with their reasons in `data/coverage/unreached.yaml`. Most are not reachability
problems: **withdrawn at source** is a work whose URL still resolves and whose publisher now serves
an empty series feed because its 掲載期間 has ended. A comparator that saw it while it was up was
not wrong, and no adapter retrieves what is no longer served — that is a state the project already
names (REQUIREMENTS §4).

### Routes, cheapest first

Each is used only where the one above it fails, and a platform reachable a cheaper way is never
listed for a dearer one.

1. **Publisher feed** — GigaViewer `/atom`, and per-series `/atom/series/<id>` which is not a
   rolling window. 22 platforms.
2. **Server-rendered pages** — comici's series-eplist markup, カドコミ's `__NEXT_DATA__`, FUZ,
   ニコニコ's `div.meta_info`. 11 platforms.
3. **Sitemap `<lastmod>`** — `adapters/sitemap/`. Published for crawlers to read; broad and
   shallow. マガポケ's carries 3,113 dated episode URLs.
4. **Generic extraction** — `adapters/generic/`, for hosts with no shared engine, driven by
   strategies proven per host rather than a selector registry.
5. **Rendering** — `adapters/render/`, headless chromium `--dump-dom`. No Python dependency and no
   driver. For platforms that build their chapter list in JavaScript: マガポケ, pixivコミック,
   マンガワン, ガンガンONLINE.
6. **Per-work, all routes** — `adapters/remaining/`, which tries all of the above against a single
   work. Used for the residue the platform passes leave behind.

### What no route reaches

- **pixivコミック's app API** returns 403 to anything that is not its own client. Its sitemap 404s,
  and `/works/<id>.json` and `/magazines/<id>.rss` both return the Next.js catch-all shell rather
  than data. Rendering reaches the same information, which is what it is used for.
- **Geoblocked hosts** (ドリコミ+, LINEマンガ, comicグラスト) refuse on location. Nothing about the
  request changes that.
- **ガンガンONLINE** publishes `次回更新：8月6日` and no historical dates at all. A reader on the
  site cannot see when a chapter appeared either.

## 4. Serialisation history

`first_publication` is the first 単行本 for every work in the catalogue, never the magazine
appearance — each record says so rather than implying otherwise. For a database whose scope is
"first published in Japan", the actual first publication is the serialisation.

MADB's magazine route was measured and abandoned: 9.3% coverage of contents overall and **zero**
for 百合姫, which is the lineage this catalogue is built on. `metadata108`, the undocumented
issue-contents relation, is the only remaining lead inside MADB.

**Path, in order of promise:**

1. 一迅社's own 百合姫 back-issue indices — the publisher lists contents per issue.
2. `metadata108` joined against cm102 issues for the 百合姫 magazine ids.
3. NDL's periodical holdings, which are per-issue rather than per-article and so probably too
   coarse.

**Cost.** Moderate for (1), unknown for (2). Worth doing before doujinshi.

---

## 4a. マガポケ was captured ten chapters at a time (closed 2026-08-04)

Kept because of what it cost to find the way through, and because the shape recurs: three separate
adapters read the same page and all three saw the same ten chapters, so the ceiling looked like a
property of the platform.

**What the gap was.** Every マガポケ record held ten chapters and was marked partial, because the
adapters read the free window and the free window is ten chapters deep. `adapters/magapoke.py` read
the episode list the series page publishes, and across 22 series it stated runs of up to 63 where
we held 10.

That was an undercount, and the reason is worth keeping. Our newest chapter was still the
newest chapter. 将来的に死んでくれ
looked like the case that would change a work's state: 42 episodes stated against our 10, filed
dormant on a date from 2019. The episode we call newest is the 42nd, so the date was right all
along and only the count was wrong. That held. Of the 37 series now captured in full, 14 gained
chapters, two gained a state they could not previously derive, and exactly one gained a date:
私に天使が舞い降りた! begins on 2020-03-11 rather than 2025-02-18. The rest already had a full
history from コミックDAYS, which carries the same series.

**What closed it.** Not the episode pages, though they would have worked. An episode page states
`episode_name` and a `start_time` in its own data layer, so the run was rebuildable at one fetch
per episode, or about 600 requests. That same data layer also names `rss_feed_url`, and the feed at
`https://mgpk-cdn.magazinepocket.com/static/rss/<title_id>/feed.xml` carries the whole series:
title, date, author and URL for every episode, in one request. 37 series, 1,956 chapters, 37
requests. It is also the better posture, since REQUIREMENTS §5 asks for the listing rather than the
reader page.

**Why the feed can be trusted.** It was checked against both things already held. The item count
equals the series page's own `episode_id_list`, and where it does not, the extra item is one the
feed has scheduled and the page has yet to publish. That is REQUIREMENTS §5's "a future date is a schedule, never a
release" arriving from a second direction. And all 202 chapters previously captured by rendering
the page agree with it on title and date.

**What the dates are worth.** `<pubDate>`, a publication date by the format's definition, and still
carrying the import signature §5 describes: all 40 episodes of ハロー、メランコリック! are dated
2021-11-11, and 46 of きたない君がいちばんかわいい's 63 are dated 2022-03-10. Those are the days
講談社 loaded a finished series onto the platform. `adapters/importdates.py` already marks such a
date unfit to headline a series and does so here without changes; 102 (work, date) pairs in the new
file trip it.

**What is still missing.** Access. The feed states none, so a chapter outside the ten-episode
window the rendered page covers says nothing about access rather than saying free.

---

## 4b. What the other platforms say about how long a series is

The same question asked of every platform that leaves a work marked partial. The answers are in
`data/coverage/series-lengths.yaml`, which build.py already reads; what belongs here is which
platforms are worth asking and which are settled.

**マンガワン prints 全23話 above the chapter list**, on every series page, over pagination that
serves ten rows at a time. The total covers the whole run, including PR rows and the 先読 rows
released early to paying readers. All six partial works are now stated.

**コロコロオンライン prints 全102チャプター** in the same position, counting numbered episodes and
extras such as 特別イラスト① alike.

**pixivコミック states no total and lists one anyway.** A withdrawn stretch stays in the episode
list as a range reading 第４話〜第６７話 掲載期間が終了しました, so the numbering covers the whole
run even where almost none of it can be opened. Reading it needs care, because the row is not the
unit on every work: 冷たくて 柔らか numbers fifteen instalments across rows called 1-① to 15-②, and
ギャル推しJK gives two instalments one row as 第2～3話. Where every row is a plain 第N話 and the
expanded numbering runs 1..N with no gaps, the count is the platform's own and five of the 23
partial works give it. The rest are recorded as instalment counts or not at all. One check comes
free: the rows a signed-out reader can open are exactly the chapters we hold, on all 23, so a
disagreement there would mean the capture had drifted.

**ガンガンONLINE states nothing**, which finishes the entry §3 opened about its dates. Its
`__NEXT_DATA__` carries a `chapters` array holding the readable window and no count of any kind:
裏世界ピクニック, at 第90話, gives nine rows. There is nothing further to fetch and nothing to
render, and the four works on it stay uncounted.

**サンデーうぇぶり states nothing.** The episode page carries neither a list nor a total, and
`/atom/series/<id>` holds only what is readable now, so a withdrawn middle leaves no trace at all.
上杉くん's newest is numbered 第34話 against thirteen entries in the feed, and that number is a
floor rather than a count, since the feed also carries 第22.5話 and five 番外編 outside the
numbering.

**コミックDAYS needs no statement.** `/atom/series/<id>` is the whole run rather than a window:
サタノファニ's 337 entries are the 337 chapters we hold, so the work is marked partial by the
adapter's own caution rather than by anything the platform withholds.

---

## 5. Conflated title/author — 13 remaining

百合ナビ's WEB連載 cells run title and author together. 40 of 53 split against titles we hold; 13
remain, flagged 作者未分離 rather than split on a guess.

**Path.** Each needs one confirmed title from the platform that carries it. Two mechanisms now
exist and both are cheap: カドコミ author pages (`/search/author/<uuid>`) embed a creator's full
work list with codes, and ニコニコ漫画 states its works as `タイトル / 作者` directly. Between
them and comic-fuz.com search, the 13 are a short afternoon.

---

## 6. Doujinshi — Phase 4, not started

Deliberately deferred at the outset. Nothing has changed to bring it forward, and the pornography
exclusion in [DEFINITIONS §2](DEFINITIONS.md) needs settling before rather than during.

---

## 7. Smaller, known

- **openBD enrichment 252/646 volumes (39%).** Older ISBNs are simply absent from openBD; not
  fixable from this end.
- **Access data is sparse.** Only COMIC FUZ, the comici platforms and ヤンマガWeb state per-chapter
  access. カドコミ falls back to a platform-wide default recorded as the project owner's knowledge,
  not as a field read from the site.
- **百合ナビ 発売日 calendar** sits captured in `data/unwired/`, wired to nothing. It is the
  natural source for a 単行本 release feed, which the catalogue tab does not currently have.

---

## 8. Capture health: three failure modes, one covered

The status page reports whether each source returned rows carrying the fields declared for it. That
answers one question of three, and the other two are invisible.

**Fields going missing** is covered. Markup changes so a field stops being extracted, the rows
arrive without it, and the deviation count rises off zero. A total failure to parse shows as an
empty source.

**Quantity moving is not covered.** マガポケ served ten well-formed episodes where the platform
published 147, for months, and no row count or staleness could see it because there was nothing to
compare against. This needs a per-run ledger: what each connector returned last time, kept so this
run can be measured against it. It is the difference between a status and a delta.

**A selector matching the wrong thing is not covered, and it is the dangerous one.** The rows are
well-formed, every declared field is present, and every value is wrong. On 2026-08-04 the generic
extractor flattened a chapter block into one run of text and 193 titles arrived carrying the view
and comment counts beside them, `3話① 26 8`, faultless by every check we run. The same day,
コミックノヴァ's commented-out promo box parsed as a real chapter and gave プリンセ「ス」 a 第8話
that was never published.

**What answers it is a landmark declaration.** Each adapter names the structural features it
depends on, the class or element or JSON key it keys off, and records at capture time whether each
was found. `adapters/comicboost.py` depends on an `h4.title` beside a `p.update-date`;
`adapters/sevenseas.py` on a `div#originaltitle`. A landmark that vanishes IS the page having
changed, stated directly instead of inferred from the damage downstream. Every adapter already
holds these patterns as regexes, so the work is recording the result rather than deriving it.

Both want doing together: they write to the same per-run record, and between them they cover all
three. Neither is small, because both touch every capture path.

### The gap list is itself hand-enumerated

`adapters/status.py` returns five hard-coded categories of outstanding work. Anything nobody
remembered to write into that function is invisible, which is the same fault as the page computing
its own numbers, one level up: a gap page that shows only the gaps somebody thought of reports clean
because it never looked.

Four things were measurable on 2026-08-05 and appeared nowhere:

- **23 contested identity anchors and 24 title-only leads.** `identity.py` prints these on every run
  and stores the leads in a queue nothing reads. A contest is one print record claimed by two web
  works, which is a decision about whether they are one work. They were 1 and 0 when the module was
  written that morning and grew with the corpus, silently.
- **71 of 121 completion verdicts unsettled**, in `data/completion-reviewed.yaml`.
- **207 rows whose state basis is Japanese prose.** That sentence is what a reader is shown to
  explain why we say a work ended, and an English reader gets Japanese.
- **Alias candidates found by eye.** `data/work-aliases.yaml` holds one hand-written entry, and
  `identity.siblings()` already detects that class automatically with 14 pairs recorded. The build
  knows how to propose these and does not.

**Invert it.** Rather than a central function enumerating categories, have the things that produce
work declare it: `identity.py` knows its contests, `curate.py` knows its strays, the completion
review knows what is unsettled. Each writes a small record of what it left outstanding and
`status.py` collects them. Then a new source of manual work reaches the page because it exists,
rather than because somebody added a line.

Same shape as the ledger and the landmark declaration, and wants doing with them: the producer
states its own condition instead of a reader inferring it.

### A staging file read as a record

`adapters/yomonga/releases.py` takes `data/source/webpages/generic-www-yomonga-com.yaml` as its
input: the generic pass produces a work list from the page, and the named adapter refines it into
`yomonga.yaml`. Two stages of one pipeline, which is fine.

What is not fine is that the intermediate sits in `data/source/webpages/`, and the build reads
every file there. So a half-parsed staging file is a record beside the refined one, and both
describe the same five works and the same twenty-four rows. The staging rows are worse:
`Chapter.1_1巻 第1話-1` where the refined file has `Chapter.16 第15話`, and the mangled
`07Chapter.12第6話-2` that reaches the phrase store and the renderer.

This is why chapter names needed a rule for index prefixes that a platform never actually prints.
The rule earns its place anyway, because コミックDAYS and マガポケ do prefix their own row numbers,
but this particular shape is our own staging output being read as though a platform had published
it.

**The fix is that an intermediate is not a source.** Either the generic pass writes a host it is
staging for into `data/queue/`, which exists so nothing there becomes a record by accident, or the
build prefers the refined file where both describe a host. The first is truer to what the file is.

There is a second hand-maintained list behind it: `adapters/generic/releases.py` skips hosts served
by a real engine using a set written by hand, so a new dedicated adapter does not claim its own
host until somebody remembers. Same class as the gap list itself.

---

## 9. The search for the name the person uses has been run once, on eleven names

Most author names on the live site are a romanisation we derived from confirmed kana. That is
mechanical and carries no note, correctly. What it hid until 2026-08-06 is that nobody had asked
whether the person writes their own name in Latin script.

**The route works and its rate is now measured rather than guessed.** Eleven of the most-published
names with no stated reading were worked by hand. Three keep a page of their own that states a
name: 焔すばる signs Homura Subaru, 秋月ルコ signs AKIDZUKI Luco, and 福井遥香's own site carries
福井 遥香（ふくい はるか） and HARUKA FUKUI. Each of those settles a Latin byline AND a kana
reading, and 焔 turned out to be ホムラ where an analyser had produced ホノオ. The other eight have
an X account or a FANBOX and no page saying how the name is read. **A handle is not a byline**:
桜庭友紀 posts as @kyomoneko_2, which romanises nothing.

So roughly one artist in four keeps a page worth citing. That is worth running and it is not a plan
for the several hundred names still carrying a machine's guess, which is what §5d's unverified mark
is for.

Where to look next, in the order likely to pay. lit.link, foriio and an artist's own site are what
produced all three above and are the first thing to try on a name. The licensed editions print a
credit, and `data/queue/english-licences.yaml` holds 87 licences whose pages carry author credits
nobody has read. Series art and platform profiles are the source that produced 49 English titles on
2026-08-04. Anthology contributor lists name people the shelf captures reach and the corpus does
not, and `data/source/webpages/bylines.yaml` now holds 46 of those lists.

**The route that is open and unfinished, and it is about titles.** BOOK☆WALKER states the reading
of a TITLE twice on the page it sells the book from: in its keywords field beside the title, and
again as furigana in the publisher's blurb, which glosses a surname on first use. 1,548 of the
3,601 titles with no stated reading have such a page, which makes it the largest single thing left
in the naming work. `adapters/names/shop_reading.py` reads it and 13 are settled; the shop answers
about one page every twenty seconds under a polite pause, so the rest is a resumable run. It says
nothing about an author's reading, because the keywords field names the author without stating how
the name is said.

**A lead deliberately not taken, recorded so it is decided rather than rediscovered.** まんが王国
prints a kana reading beside every author it lists, and コミックシーモア and DMM do the same on
some listings. A licensed retailer is not a community database, and `curate.py` names "a bookshop
listing" as evidence a reviewer may weigh under `researched`. It was left because `researched` says
a person weighed the evidence and applying it to four hundred names mechanically is a bulk import
wearing a reviewer's label. The shops also disagree with each other: DMM files 桜庭友紀 as
さくらばゆうき where another listing gives さくらばゆき. The bounded version is worth doing, over
the names where a shop's kana DISAGREES with the analyser, because those are the ones a reader is
being shown wrongly today.

The 179 whose pronunciation is unconfirmed are a different problem and are already marked as such.

### 先読み is read as free on 一迅プラス

`ひなちゃんが生きてるなら` 第8話 is 先読み: the page says 「165ptで今すぐ読める！」 and
「2026年08月27日に無料公開予定」. We record it `free-timed`, and the interface counts that as free,
so a reader is told the newest chapter costs nothing when it costs 165 points for another three
weeks.

**The rule is already written and already correct.** `adapters/gigaviewer/series_feeds.py` says in
as many words that a chapter which is paid now and free on a stated date is `purchase` and not
`free-timed`, and that `free-timed` means readable RIGHT NOW at no cost, merely rate-limited. That
comment was written after the same mistake told a reader every chapter of ゆりゆりぱにっく was free
when 18 of 24 cost 80pt.

**What defeats it is the order of the tests.** Ticket eligibility is checked before the scheduled
branch, so a 先読み chapter that is also ticket-listed is settled as `free-timed` and never reaches
the check that would call it `purchase`. The scheduled set is built by probing chapters already
classified `paid`, so a chapter the ticket test claimed is never probed, and the branch that knows
about 無料公開予定 cannot see it.

The bisection compounds it. It assumes ticket eligibility opens with age and finds a single
boundary, and this work is not monotonic: 第8話 and 第6話 to 第3話 read as ticket while 第7話, 第2話
and 第1話 read as unconditionally free. A boundary search over a non-monotonic sequence returns an
answer with no warning that its assumption failed.

The fix is to read each chapter's own state rather than infer it: 先読み and 無料公開予定 are stated
on the episode page, so a chapter carrying either is `purchase` whatever the ticket probe said, and
the scheduled test runs before the ticket test rather than after it. Both shapes want a fixture in
`adapters/gigaviewer/test_series_feeds.py` quoting this page.

## 10. The ISBN population arrived with no names (2026-08-05)

296 works entered from コミックシーモア's shelf by way of their ISBNs, and no name pass has seen
any of them. Three budgets were accepted on that basis rather than because the numbers are
acceptable:

| Budget | Was | Now |
|---|---|---|
| works showing a romanisation | 53 | 288 |
| works without English | 12 | 20 |
| uncertain readings | 13 | 17 |

The loud one is the first. A work with no English title is shown by a romanisation of its Japanese
title, so the figure counts works the interface is presenting through a transliteration nobody
published. That is a queue and not a new normal, and the budget comes back down as the passes run.

What each needs is different. A romanisation is replaced by an English title, which is either a
licensor's or ours and is marked as ours where it is. A reading is settled by openBD where the
work has an ISBN, which this population does by construction, so `openbd_reading.py` can reach
most of it without a title search. Nothing here needs a decision; it needs the passes running over
a population that has not had them.

The same arrives again when the BOOK☆WALKER capture finishes and its ISBNs go through the same
route.

Stripping MADB's role brackets off the print credits took uncertain readings from 17 to 22. The
names were `[著]秋山はる` before, which matched nothing in the name store and so counted as
nothing; they are people now, and five of them have no settled reading. The number went up because
the data got better, which is the ordinary shape of this measure.

## 11. A shop states ISBNs on first volumes (2026-08-05)

コミックシーモア marks 1,024 of its 1,833 yuri works 完結, and 382 of those join our corpus by
ISBN. That answers whether a series finished, and 258 works published only in volumes now say so
where nothing said anything before.

Which volume ENDED a series is a different question and this capture cannot answer it. The rule is
sound: where the shop states 完結 and states N volumes and N were read, the Nth ended it. In
practice 207 works pass that test and every one of them has a single volume, so the claim is true
and says nothing. The cause is that the shop states an ISBN on 618 of 7,262 volumes read, and
overwhelmingly on the first of a series.

**Closed 2026-08-06, and the guess in it was wrong.** BOOK☆WALKER was going to rescue this by
carrying ISBNs deeper into a series. It carries none: its capture finished at 2,423 works and 5,709
volumes with an ISBN on not one of them, because the shop sells files, which its own adapter had
recorded when the capture covered 870.

What settled it was that the shop never had to name the volume. It says the series is COMPLETE and
says how many volumes it has; our own record says which volume is the Nth. Each side answers what
it knows, and 121 volumes are marked where 0 were before. Asking the shop for an ISBN it does not
print was the wrong question, and it took a capture of 2,438 works to notice.

Five works have a shop saying 完結 while a platform is still publishing them. The platform wins and
the disagreement is counted at build time rather than resolved.

## 12. Checks that inferred the corpus (audited 2026-08-06)

"Is this a work we hold" is asked in several places and had no stated answer, so each caller
assembled one from whatever artefact was to hand. `build.py` now writes `data/build/titles.json`,
and the audit found three callers guessing:

| Where | What it asked | What it used |
|---|---|---|
| `names/curate.py` | does this curated title name a work | the 14-day feed window and `series.json` |
| `names/inputs.py` | which works do the name passes run over | `series.json` and a hardcoded `feed/2026-07.json` |
| `gigaviewer/releases.py` | is this feed title a work we already have | `index.json`, the PRINT catalogue, plus one platform's series list |

The third was the largest: 669 titles counted as established where the build holds 1,481, so 812
web serialisations had to be rediscovered through the Tier C yardstick on every run. The second had
not fired yet and would have failed silently, because a month named by hand goes stale by the
calendar and a name pass that stops seeing new works looks exactly like a name pass with nothing
to do.

`check.py` was examined and left alone. Its budgets measure what a reader sees, so `series.json` is
the right denominator, and it already reads every month archive rather than the window.

What remains: `titles.json` states titles, and a title is not an identifier. The works that reach
it under two spellings are folded by each consumer to its own rule, which is right for the callers
above and would not be right for a caller asking about a specific work. That one should ask
`data/identity/works.yaml` for an id.

Two more works show a romanisation as of 2026-08-06, taking the budget to 290. They are
転生王女と天才令嬢の魔法革命 【タテスク】 and 雨。のち、晴れ！, which a カドコミ run had deleted by
not carrying over the works it failed to fetch. They are back, and works that exist need names.

## 13. BOOK☆WALKER's shelf, joined presumptively (2026-08-06)

1,737 works entered from BOOK☆WALKER's yuri shelf on the project owner's decision: join on the
title, watch for edge cases, because being wrong later about a small number does not outweigh
holding two thousand more. 517 carry a print date the shop states; the rest say why they do not.

This is the first source admitted as a WORK source that is not a catalogue or a publisher. The shop
states no ISBN on any of 5,709 volumes, so no Tier A or B record is reachable from its shelf and
there is nothing to promote in its place. `bookwalker` therefore sits in ALLOWED_SOURCES at the
lowest priority, carries no marketing_label, and every record names the shelf that admitted it.

**402 works are waiting for a person**, in `data/queue/bw-review.yaml`. Their titles already name
works we hold, which is the strongest lead available here and no kind of identifier at all. Nothing
merges on it.

What this population still owes: 1,980 works show a romanisation rather than an English title, up
from 290, and the readings behind them are the analyser's. That is the same debt the コミックシーモア
population brought and it is now four times the size.

## 14. BOOK☆WALKER volume counts are understated (2026-08-06)

Checked after 黒の世界は白墨に染まる showed the ingest keeping imprints in titles. The counts are
short in two ways, one measurable and one not.

**Measurable, and small.** 9 works are shorter here than another source says they are, mostly by
one volume: 私に天使が舞い降りた! holds 15 against 16, citrus 9 against 10. 吸血鬼の花嫁 is the real
one, holding 1 against 8.

**Not measurable, and large.** 1,175 works were captured from a single volume page with the series
page never read, and 931 of those single volumes name a `series_id` in the capture that nothing
followed. A work recorded as one volume may be a series of unknown length, and the date on its one
volume is only a first publication if that volume is really the first. The remaining 244 name no
series and are standalone.

This bears on dating more than on counting. `adapters/recon/bookwalker_volumes.py` already has the
series-reading path, so the 931 are reachable; nothing has followed them yet.

### The listing was paginated and this module read page one (found 2026-08-06)

Following the 931 turned up a fault underneath them, and it is the worse of the two because it was
invisible. `/series/<id>/list/` serves 60 rows to a page and links the next, and
`bookwalker_volumes.py` read the first page and stopped. `recon/bookwalker_shelf.py` passes 60 to
its own pager for the same listings, so the page size was already written down in this repository
and one of the two readers of it did not have it.

Nothing looked wrong. The rows were well-formed, every declared field was present, and the works
came back holding 60 volumes. What gave it away was the shape of the distribution: six rows sit at
exactly 60 and nothing at all sits between 39 and 60, which is a page size showing through as a
property of the shelf. 付き合ってあげてもいいかな【単話】 read as a 60-volume series and holds 133.

The date pays for it as well as the count. `first_publication` is the earliest 底本発行日 across
the volumes read, so a work cut at page one has its first publication chosen from whichever 60 the
shop sorted first.

**What settled it.** One reader for one listing, walking pages until a short page says there is no
more. A pager states the two or three pages around the current one rather than the last, so reading
a total off it means trusting a window to name an end it does not know; a short page cannot be
misread. Rows carry `pages_read`, which is what tells a row cut at 60 from a series that genuinely
holds 60, and a capped pass repairs those before it goes looking for series nobody has opened.

**`bookwalker series unread` is the budget**, counting both classes, and it reaches zero because
every row it counts names a series to fetch. The follow is one request per series plus one per
volume the shelf never linked, so it is a long resumable job rather than a hard one.

## 15. The 404s that were never pages (2026-08-06)

Fifteen works were carried as a licence we could not cite: the English name is one an English
reader would recognise, and the licensor's page for it returned 404, so `licensed` was refused and
each was published as a translation of ours. That reading was wrong about fourteen of them, and it
is written down here because it is a mistake that reproduces itself. **An anime licence is not a
manga licence**, and the familiar English name for a Kirara-style series usually comes from
Crunchyroll, Funimation or Sentai, which name the adaptation.

**What was checked, per work.** Seven Seas' live catalogue, read whole from its own sitemaps: 1,208
series pages, 6,378 book pages, 1,240 posts and archive pages, plus the site's own search. Yen
Press's live catalogue, likewise: 1,635 series and 15,672 title pages. Then the Internet Archive's
index of what those addresses used to hold, 2,814 Seven Seas series URLs and 7,043 book URLs. That
last is what settles it. **There is no gone page.** Seven Seas never published a page for Sakura
Trick, Komori-san, Wataten!, Comic Girls, Slow Loop or Ms. Vampire, so nothing 404s that ever
resolved, and the licence the 404 was taken as evidence of does not exist.

| Work | Disposition |
|---|---|
| リコリス・リコイル | **Licensed.** Yen Press, `https://yenpress.com/series/lycoris-recoil-manga`, joined on the credit: the catalogue names Spider Lily and Yasunori Bizen, our record credits 備前やすのり / Spider Lily. Recorded. |
| 推しが武道館いってくれたら死ぬ | **Licensed, not citable.** Tokyopop holds it. This project does not read tokyopop.com, whose robots.txt carries instructions addressed to agents and a checkout endpoint, so there is no page to cite and the English stays ours. |
| ゆるゆり | **Licensed once, by a publisher that is gone.** ALC Publishing put two volumes out on JManga, which closed in 2013. No live page can exist. |
| 桜Trick · 小森さんは断れない！ · 私に天使が舞い降りた！ · となりの吸血鬼さん · スローループ · こみっくがーるず · ひとりぼっちの○○生活 · スロウスタート · ステラのまほう · 城下町のダンデライオン · たくのみ。 · おちこぼれフルーツタルト | **No English manga licence.** Absent from both live catalogues and from both archived URL spaces, and no English print publisher is named for any of them. Each keeps the translation it has, which is ours and is marked as ours. |

あんハピ♪ was on the same list and came off it in `cede271`: that licence is real, Yen Press
publishes it, and its page was live all along.

**One thing to fix in the fetching, not in the data.** `sevenseasentertainment.com` answers 403 to
`net.py`'s user agent and 200 to the same request identified as `yurarium/1.0
(+https://yurarium.github.io)`. The block is on the `Mozilla/5.0 (compatible; ...)` prefix, which
is a bot signature at the hosting layer rather than anything about this project. Two earlier passes
recorded that the licensor "refuses automated fetches" and cited a distributor instead; it does
not, and the whole catalogue reads in a few minutes.

## 16. A date rule for anthologies, tested and refuted (2026-08-06)

Where a MADB volume matches a series on the title alone, `extract.agrees` requires the creator, the
publisher or the imprint to agree as well. An anthology names nobody, so the proposal was a fourth
test: for 一迅社 anthologies where neither record names a creator, take an exactly agreeing
publication month. It appeared to settle 25 joins. **It is refuted**, and the counter-case is
pinned in `adapters/madb/test_extract.py` so the rule cannot be re-added quietly.

**It joins nothing.** Across all 401,311 book records in release 1.2.18, `agrees` refuses 1,195
title matches. 89 of those name no creator on either side, and none of the 89 has an agreeing
month, because MADB leaves 607 of the 1,195 series records undated. The same measurement on the two
other joins the rule could have meant returns zero as well: the shop-to-print queue's 301 title
matches all name a creator on the shop side.

**Where the 25 came from.** The works list, where a print-only row carries its own
`first_publication` date twice, as the row's `first` and inside its `print` block. 54 creatorless
pairs agree on the month there, and every one of the 54 is a row being compared with the print work
it already carries. The number was one fact read twice.

**And it would break the class it was drawn from.** A tie-in anthology is raced out by rival houses
in the month the game ships. ペルソナ4コミックアンソロジー is two different books in 2009-01, one
光文社 and one 一迅社; To heart 2アンソロジーコミック is three in 2005-07 under three publishers. 17
creatorless title-and-month groups in the release name more than one publisher, so an agreeing
month is evidence about a release date.

**The premise was wrong too.** citrus is catalogued as 一迅社 and as `[発売]講談社` with no creator
on either record, and the imprint is IDコミックス on both sides, so the existing third test already
joins it. Nothing was left for the date to carry.

## 17. A third of the national bibliography answered nothing (2026-08-06)

Four modules had a function called `isbn13`. Two converted a ten-digit ISBN to its thirteen-digit
form and two only stripped the punctuation out, and the name did not say which was which.
`madb/isbn_dates.py` was one of the strippers, so the index it builds over metadata101 was keyed on
the ISBN as the catalogue happened to print it. MADB prints **126,318 of its 355,323 ISBNs in ten
digits**, 35.5% of the file, because it imported those records from NDLサーチ as they were
catalogued. Every question this repository asks is thirteen-digit, so a third of the bibliography
answered nothing and read exactly like a catalogue with no record of the book. `madb/by_isbn.py`
carried the same stripper under the same name and could not see those records either.

It surfaced through §11, which left 51 コミックシーモア works filed `isbn-stated-not-catalogued`,
meaning the shop states an ISBN and no catalogue asked holds it. Grepping all seven bulk files for
the ten-digit form of each found two of them: ハニー＆ハニー at 2006-04 and フリー・ソウル at
2004-08.

**Closed.** `adapters/isbn.py` is the one converter and all four modules consume it. The index is
keyed on the thirteen-digit form and its file is named for that, so a stale index cannot answer.
The count fell, from 347,875 entries to 346,826. The ten-digit records were always indexed, under
a key nothing asked for, so what changed is which questions reach them, and the 1,049 lost are
books the catalogue holds in both forms and now holds once.

That leaves 49, and MADB is not where they are: all seven bulk files were searched for both forms
of all 51. They are 一迅社 titles in two blocks, 4-7580-70xxx from 2006 to 2010 and
978-4-8251-xxx and 978-4-7580-99xxx from 2024 onward. The second block is not a staleness problem,
because release 1.2.18 holds 7,379 volumes published in 2026; it is that MADB holds four records in
the whole of 一迅社's new 978-4-8251 prefix. openBD answers null for every one of the 49.

### 出版書誌データベース (Books.or.jp) holds them, and its terms do not let us store them

REQUIREMENTS §1 lists Books.or.jp as Tier A with its access unverified. It is verified now.
`robots.txt` is `Disallow:` with nothing after it, `/book-details/<isbn>` serves a server-rendered
page, and that page states the ISBN, the publisher, 発行年月日 and 発売日: 少女美学, which neither
MADB nor openBD holds, is 一迅社, 2006年09月, ISBN 9784758070041.

**The terms are the obstacle and they are not ambiguous.** 利用規約 第3条 permits use for
non-profit purposes, which this is. 第4条 states that the information and images on Books are
protected by JPO's rights and that reproducing, diverting or selling them by any method without
the rights holder's permission is not allowed. A publication date copied into a public repository
is 転用 on the plain reading.

So this is **a decision for the project owner and not a gap to be worked through**. The site
answers what we need and the terms say we may not take it away with us. STANDING-INSTRUCTIONS §9
is the rule that applies: read the declaration before depending on it. What would settle it is
asking JPO, whose contact form is on the site.

Nothing from Books.or.jp is stored anywhere in this repository, and no adapter for it was written,
because an adapter whose output may not be used is worse than none.

**How much the question is worth, measured rather than assumed.** A sequential polite sweep of all
49 was run once. **36 resolve to a book page and every one of the 36 states a publication date**:
33 on the first pass and 3 more on a retry, across both blocks, including 少女美学 and voiceful
from 2006 and the 978-4-8251 titles from 2025. 7 returned no record. The remaining 6 are unresolved
rather than absent, because the host starts refusing a sequential reader after about forty requests
and the retries were not completed.

So the answer is that Books.or.jp holds at least three quarters of what neither other catalogue
does, dated, and that a run against it needs a slower schedule than either catalogue we already
use. Neither of those matters until the terms question is settled.

## 18. Where the last 57 commercial-imprint rows stand (2026-08-06)

89 undated BOOK☆WALKER rows sat on imprints that print books, so a dated volume with an ISBN
exists for each and the shop simply does not hold the number. `madb/by_title.py` dated 32 of them,
and 25 more elsewhere in the undated population where the shop's imprint had said the work was
digital-only and the bibliography said otherwise. What is left, with what each one needs:

| | |
|---|---|
| **25** | the bibliography holds no 単行本 under the title. Not a title-form problem: the creators ARE in MADB, with 68 records for なもり, 20 for ばったん and 18 for merryhachi, and none of them is the work. 20 of the 25 reached the shop in 2024 or later and 9 of those in 2026, so this is the bibliography's import lag and a later release answers it at no cost. |
| **12** | a digital single sold by the chapter. Ten are the SM百合えっちアンソロジー series, where each 【単話】 is one contributor's story out of an anthology and nothing was printed under that title. |
| **9** | a 小冊子 or a 画集: the booklet given away with a volume, and one art book. Not a commercial publication, no ISBN, and `by_title.keys` deliberately does not fold either onto the work it accompanies. |
| **6** | コミックシーモア states an ISBN and no catalogue asked holds it, which is §17's population reached from the other side. Books.or.jp is where those are. |
| **3** | the title matched and the join was refused. `Memories` is the refusal working: 大友克洋's MEMORIES and a 1991 大陸書房 book share the folded title and neither is the work. The other two are anthologies MADB credits to nobody, and a record naming nobody agrees with nothing. |
| **2** | an anthology with two dozen contributors and no MADB record under the title. |

### What the shop's imprint could not tell you

The 25 dated outside the 89 are the more interesting half. Their rows were filed `no-print-edition`
or `print-edition-unknown`, which is `bookwalker_volumes.py` reasoning from the imprint: a label
that states 底本発行日 on none of its volumes has no print edition to date. That is sound about the
LABEL and wrong about these WORKS, because a doujin distributor and a digital-first imprint both
resell books somebody else printed. 蝋燭姫 and 化け猫システム are 角川 and ワニブックス books that
ナンバーナイン now sells under 百合コレ, パロスの剣 is a 1987 あすかコミックス volume, and
お江戸とてシャン is 芳文社's. The imprint was never going to say so; the bibliography does.

## 19. The 49 undated ISBNs, closed at the publisher (2026-08-07)

§17 left 49 コミックシーモア works stating an ISBN that neither MADB nor openBD holds, and stopped
at 出版書誌データベース because 利用規約 第4条 forbids 複製・転用 of what the site states. That was
the right place to stop and the wrong place to look first.

**Every one of these 49 is a book with a publisher, and a publisher stating the date of its own
book is first-hand.** REQUIREMENTS §1 files publisher sites in Tier B against Tier A for the
catalogues, and that ordering settles which source to believe when two of them speak. Here no Tier
A catalogue speaks at all, so the question it settles does not arise. `adapters/publisher_dates.py`
asks the publisher and answers **47 of the 49**.

45 of them are 一迅社, which runs its own bibliographic site at `data.ichijinsha.co.jp` keyed on the
eight ISBN digits between the 978-4 prefix and the check digit, serving no robots.txt at all. Of
the rest, 幻冬舎コミックス answers an ISBN search and states 発売日 in its 書誌情報; 双葉社 renders
its book pages client-side and its own script reads them from `book-api.futabasha.co.jp`, whose
robots.txt is `Disallow:` with nothing after it, so the JSON record is asked for instead of the
page.

### The two the publisher route did not reach, and the owner's decision on the fallback

芳文社's site returns nothing for エンドレスルーム or for its author under either name, and neither
ぶんか社 nor 主婦と生活社 has a record of シークレットガーデン, a 1995 エメラルドコミックス volume
whose ISBN prefix says 主婦と生活社 while the shop's row says ぶんか社. Both searches were shown to
work on a title the same site does hold, because a search returning nothing looks exactly like a
search that broke.

**That row's stored venue is still the shop's ぶんか社**, because `first_publication_venue` is
derived from the shop's publisher field and one producer of a fact is the rule. Books says
主婦と生活社 and the ISBN prefix 4-391 agrees with Books. Scope is unaffected, since both are
Japanese publishers and §6 turns on the country, and whoever promotes this row has to settle which
name goes in the record.

**The project owner decided on 2026-08-07 that Books.or.jp may be asked where the publisher route
has genuinely failed**, and the reasoning is recorded here so nobody has to reconstruct it. A
publication date is a fact and carries no copyright. Japan has no sui generis database right, and
著作権法第12条の2 protects a database's selection and structure and not the facts inside it. Asking
a database to resolve ISBNs already held takes none of its selection. What is left is a contractual
term of uncertain force, and the decision is to rely on that reading for the remainder.

So `adapters/booksorjp.py` exists now, and its output is marked. `first_publication_basis` reads
`books-or-jp-registration` for those two rows against `publisher-own-page` for the other 47, and
`first_publication_source` names the page each date was read off, so an aggregator-sourced row can
be found and replaced the day a publisher page appears. `check.py`'s `per-book dates cite their
page` is the invariant that keeps the citation from going missing.

### 発行年月日 from the aggregator and 発売日 from the publisher, which is deliberate

Books states both, and on these records 発行年月日 is a month while 発売日 renders that month as its
first day: シークレットガーデン is 1995年09月 and 1995年09月01日. DEFINITIONS §6 names a
first-of-the-month standing in for a month-precision record as one of the dates that has already
produced a wrong answer in this project, so the field taken from Books is the one that invents no
day. A publisher stating 発売日 2006-09-16 for its own book is stating a day it chose, which is why
that route reads the other field. None of the 47 publisher dates falls on the first of a month.

Both routes sit below MADB and openBD in `cmoa_volumes.PREFERENCE` and above the shop's 出版年月.
発売日 is the on-sale convention and the catalogues carry the 奥付 date, the two run about a month
apart by construction, and §17's own measurement is why one field must not hold two conventions.
The ordering is moot for these 49, where no catalogue holds the ISBN, and it is written down so it
stays right for the first row where one does.

### One of the 49 ISBNs belongs to a different book

cmoa states 9784758062862 for える・えるシスター 1巻. 一迅社's own page for that ISBN is 白砂村 (7)
by 今井神, and the shop's own page names 邪武丸, whose える・えるシスター (1) is 9784758061193 at
2008-11-08. The page for the wrong ISBN parsed, stated the ISBN asked about and stated a date, so
every mechanical signal said the row was answered; only comparing the publisher's title against the
shop's caught it. `publisher_dates.same_work` is that comparison and its counter-case is pinned in
the test, because 一迅社 writes レンアイ♥女子課 where the shop shelves レンアイ・女子課 and a
tighter rule would reject the pair.

The shop's number is left in the capture exactly as the shop states it, with the publisher's beside
it as `publisher_isbn`. The file is a record of what cmoa says, and rewriting the ISBN would lose
the disagreement, which is the part worth keeping.

**Closed.** 49 asked, 47 from a publisher's own page, 2 from Books.or.jp, none unreached, and the
two sources never disagreed because no book was answered by both.

---

## 20. The web works with no print edition, worked platform by platform (2026-08-07)

862 of the 3,083 works held had a web serialisation and no tankōbon, no volume count and no ISBN.
The print catalogue is reached by imprint and by a retailer's yuri shelf, and a work serialised on
a general platform is on neither, so nobody had asked the source that knows: the platform itself,
which links from a series to the shops selling its volumes.

`adapters/editions/` reads those links and `adapters/madb/by_platform_isbn.py` takes the ISBNs to
the national bibliography. 862 fell to 648. What follows is what is left and why.

### The residual is mostly a real absence, not an unread source

Of the 839 platform addresses asked, 293 led to a printed volume, 520 met a platform that lists no
collected volume for that series, and 26 met a volume the platform lists without stating a number
anybody can read. The 520 are the answer to the whole question: most of these works are 読み切り or
a serialisation too young for a tankōbon, and no further fetching moves them. They are worth asking
again later, which is why every one of them is in `data/queue/platform-editions.yaml` with the
reason recorded rather than being absent from it.

### Platforms whose links reach no printed edition

**少年ジャンプ+ (45 works, 0 reached).** Its コミックス block offers ゼブラック, ebookjapan and an
Amazon link to the Kindle edition. Every one identifies a file; none states an ISBN. This is not a
parser limitation and a further pass will not fix it, because 集英社 does not link the printed book
from this platform at all. となりのヤングジャンプ, the same publisher, links `s-manga.net` with the
ISBN in the query string, so the difference is per platform rather than per publisher.

**COMIC FUZ (25 works).** Volumes are sold inside the platform's own store and no page links out.
The rendered series page names the imprint and states no number.

**マガポケ (17 works remaining).** The page carries no 単行本 section and no outbound shop link. Its
title API answers `invalid hash.` without a request signature the site's own bundle computes, and
this project does not replay one, for the same reason it does not replay comici's Bearer token.

**マンガPark (9), マンガワン (5), コロコロオンライン (2), コミックノヴァ (2), フラコミlike! (1),
ゼロサムオンライン (1).** Read and carrying no outbound shop link. マンガよもんが (5) links booklive,
Renta! and an `amzn.asia` short link, none of which states a number without being followed, and its
five works are not worth a redirect apiece today.

**ニコニコ漫画 (1).** Links BOOK☆WALKER, which states no ISBN anywhere (§14 measured this).

**bylines (7).** Not a platform: the rows are one-off serialisation pages at seven different hosts.

### Where a shop's number belongs to another book

Three leads were refused because the bibliography's title for the record named something other than
the serialisation the ISBN came off, and all three are worth keeping because they are three
different failures:

くらげバンチ's sidebar on ストロベリークォーツ lists けがわとなかみ, which is the same author's other
series. ビッコミ's 単行本情報 on the one-shot 人魚姫 lists ベラドンナの恋人, the author's collected
volume, so the platform is stating a relation that is not "this work's volumes". コミックシーモア
states 9784046804099 for 両片想いな双子姉妹 1 and that ISBN is 百合百景, which is the same shape as
the える・えるシスター error in §19.

The check that caught them compares titles. It is a guard and not a join: the join is the address
the ISBN was found at. `by_platform_isbn.agreement` reports every comparison and the run
prints the refusals, so a platform that starts advertising its neighbours shows up as a number.

### What would be worth doing next

The GigaViewer コミックス page at `/comics` states ISBNs for the current month's releases and links
the series' first episode, which is a join. It reaches works whose series sidebar already answers,
so it adds little today and would accumulate if run monthly. `adapters/editions/platforms.py` holds
the parser and `gigaviewer_comics` is tested; nothing runs it yet, which is the one produced thing
in this change with no consumer.

BOOK☆WALKER's `ecode` appears on every カドコミ volume and identifies an edition. It is not followed
because BOOK☆WALKER states no ISBN, so the chain ends there.

The 75 カドコミ works listing no volume are the largest single block left. カドコミ is a publisher's
own platform, so its silence is that publisher saying it has collected nothing yet.

### The three anthologies still crediting nobody, and the route that does not reach them

`百合姫selection` (C280370, 2007-06, 百合姫books), `Wildrose Re: mix` (C357074, 2011-02) and
`Girls Love` (C364412, 2011-08), the last two on IDコミックス / Yuri-hime comics anthology series.
An anthology's author is a table of contents, and no source we hold states one.

The route that settled `Yrhm百合姫20thアンソロジー` was the magazine's own site, which keeps a
作品紹介 page per title and states the line-up under ＜COMICS＞. It does not reach these. The
アンソロジー category path answers with an empty document and the 百合姫 front page names none of
the three, so the site carries current titles and not a fourteen-year back catalogue. 一迅社's book
database at data.ichijinsha.co.jp was already measured as answering 404 for that era, and
コミックシーモア files them under アンソロジー while selling no 単話, so there is no per-story row
to read a contributor from either.

What is left is the books themselves. A scan of a table of contents is not something any source
here publishes, so this stays open until a copy is read.

---

## 21. The printed works whose serialisation nobody had looked for (2026-08-07)

§20 ran the corpus one way: from a serialisation to the shop selling its collected volumes, to the
ISBN, to the national bibliography. That brought 862 web works with no print edition down to 648.
This ran the other way, from a printed book to the run it was collected from. **2,063 print-only
works fell to 1,724**, and the 1,020 web rows became 1,352.

### The publisher says who to ask, and not where to look

The plan this started from mapped each publisher to the platform it runs, and it is wrong.
`運命のヤマダダダダダダダダダダ` is the case that settles it: the book is 芳文社's, printed under
Manga time KR comics, 芳文社 runs COMIC FUZ, and the serialisation is on ニコニコ漫画. Measured over
the whole pass, **319 of the 362 works joined were found on ニコニコ漫画** and only 41 on COMIC FUZ,
so the platform a publisher owns is a minority answer even for that publisher's own books. Both
search routes are publisher-blind for that reason.

### Two searches, and only one of them may settle anything

`manga.nicovideo.jp/search?q=` is server-rendered and states the title, the author and the work id
in every result, so a hit there is the platform speaking (Tier B). `webcomics.jp/search?q=` covers
96 platforms in one request, which is the fan-out reducer REQUIREMENTS §5 describes, and it is Tier
C: it turned "somewhere among 96 sites" into one address and settled nothing. Every lead was then
taken to the platform's own page and tested for agreement on the creator, the publisher or the
imprint (RUNBOOK §11). `adapters/serialisation/` holds the search, the confirmation
and the promotion.

Both sites state an empty result in words, which is what makes "asked and found nothing" a
different row from "we could not read the page". Of 2,068 works asked, **1,606 got a stated nothing
from both** and 2 left one site unanswered.

### Where the agreement came from, and what refused

23 leads were refused because the platform credits somebody else, and every one is right: ニコニコ
carries a 東方 doujin called サラダボウル by TJLJFJLJ against 講談社's book by きぃやん, and 創作百合,
百合漫画短編集, ふたり, 約束 and Memories each match two or three unrelated works. A generic title is
where this guard earns its keep.

Two fields did most of the work and one of them was new. ニコニコ prints a copyright line,
`(C)おにぎりパクパク/芳文社`, which is the only place a Japanese platform routinely names the
**publisher**; COMIC FUZ tags a series まんがタイムKRコミックス, which is the **imprint** printed on
the volume. Both are §11 fields and neither is a person, so they joined books whose two sides write
the author differently.

### What is left

| | |
|---|---|
| **1,606** | asked, and both searches stated they have nothing. Almost all are the 1,151 undated BOOK☆WALKER rows: 519 ナンバーナイン, 148 クロスフォリオ出版, 81 ライトリーズン and the rest are digital-first labels whose books were not serialised on a commercial platform. |
| **58** | a lead whose page states no author, so nothing but the title agrees. 16 are pixivコミック, which is closed to us by the operator (§2 above), and the rest are one or two works each on 24 hosts. |
| **25** | joined, and the platform's chapters not yet read, so the row is still print-only. 8 カドコミ works whose episode list is empty, 4 一迅プラス, and 13 single works on hosts with no adapter. |
| **23** | refused, correctly. |
| **19** | the page could not be read: 7 LINEマンガ, which geoblocks us (`data/platforms.yaml`), and 12 dead links. |

### The 212 一迅社 rows are the sharpest miss

Not one of them joined. They are the undated BOOK☆WALKER half of the 百合姫 line, and 一迅プラス is
a platform this project already reads, so a serialisation would have been found long ago if it were
listed under the same title. What the searches say is that these books were serialised in the
magazine and not on the web, which is §4's gap rather than this one's.

### Two faults this pass surfaced, both fixed here

**A cache key that dropped the host.** `net.cache_key` kept the last 120 characters of the
sanitised URL, and a percent-encoded Japanese title is 90 characters on its own, so two different
sites asked the same question shared one cache entry. Searching ニコニコ and the antenna for one
title served ニコニコ's page to both, and the antenna was recorded as having answered when it had
never been read. Any adapter caching several hosts in one directory has the shape;
`adapters/editions/capture.py` walks five engines into one.

**A refresh that removed works.** `comicfuz/releases.py` takes its targets from the gap report,
which by construction lists only works reachable nowhere else watched. A work that becomes
reachable elsewhere leaves the gap file, and the next FUZ run then stopped asking about it and
dropped it from `data/source`: a run meant to add 42 discovered works removed 24 held ones,
恋する小惑星 and アネモネは熱を帯びる among them. That is REQUIREMENTS §4's forbidden shape. It now
carries over what it did not target, as カドコミ's adapter already did.

### A row's address is a chapter address, and chapter addresses move

`build.py` gives a row the address of its newest chapter, and `identity.py` anchors the work on the
row's address. On every GigaViewer platform those are the same thing, so a work publishing a
chapter can change the address its identifier was minted against. Five works changed hands on
2026-08-07 when the chapter-count rule changed and their 一迅プラス runs came to outnumber their
コミックDAYS ones; each was about to be minted a second identifier for a work already held.
`data/queue/address-moved.yaml` repairs those five and states the evidence. **The fault itself is
open.** The fix is for a row to keep a stable work-level address where the platform has one, which
`nicovideo/works.py` does by emitting no per-chapter URL at all.

### What would be worth doing next

The 16 pixivコミック leads are works we can name and cannot confirm, and that is the operator's
choice rather than a matter of effort. The 8 カドコミ works whose episode list is empty are the
cheapest remaining block: カドコミ answered for each of them and listed no episodes, which is worth
asking again rather than reading as an absence. Nothing else in the residue is worth more than one
work per host of effort.

### The Atom feed needs neither thing I said it needed (2026-08-07)

Two prerequisites were named for an Atom feed of the updates view, and measuring both found nothing
to do.

**Access-change direction is already recorded.** The claim was that a row says an access change
happened without saying which way, so only the opening direction could not be published. Every
release row carries `became_free`, set where the chapter list is read, and the reading was taken
from a JSON dump truncated before that field. Rows that were once emitted as `type: access-change`
now reach the feed as `chapter` with `became_free` on them, which is the same fact in a better
place.

**Nothing is clustered.** The claim was that an instalment split across entries produces several
feed rows for one thing, on the evidence of うさぎはかく語りき showing 第5話(1)(2) and 第6話(1)(2) on
one day. Grouped by work, date and part-stripped title, the current window holds **0** such groups
in 191 rows. The window had moved on and the earlier reading was of a state that no longer holds.

So the feed can be built from the rows as they are. What remains true from that design is the part
that was never about the data: ids minted once, `updated` taken from when a release was seen rather
than from the build clock, archives keyed on `seen` so a late discovery lands in an open month, and
two documents so a title is never half-Japanese.


### §21's fault, half closed (2026-08-07)

A row's address is its newest chapter's address, so on a GigaViewer platform it moves whenever the
work publishes, and `identity.py` mints a second identifier for a work it already holds. 535 of the
1,352 web rows were exposed.

`identity.stable_url` now reduces a chapter address to its work's address before the anchor is
built, so two chapters of one work give one anchor. The 28 rows whose address carries the work's own
address in front of it, `/title/03056/episode/441581`, are closed. The stable anchors were attached
to the existing identifiers first, so nothing was minted and nothing retired: 3,155 identifiers
before and after.

**507 rows are still exposed** and cannot be closed from what we hold. `comic-days.com/episode/
12207421983997344603` is a chapter id and the whole path, so the work's address is not in the string
and inventing one would be inventing an address. `series_url` reaches only カドコミ and COMIC FUZ,
and never a series row. Closing these means capturing each platform's work-level address, which is a
fetch and not an edit.

### §21's fault: the addresses are read, and build.py has the last move (2026-08-07)

The fetch above was done. All 507 rows were read, 507 work-level addresses were established, and
each was attached to the identifier its work already answers to. `identity.py` reports 3,155
identifiers and 0 new, and `check.py`'s new budget `rows with a moving address` reads 0 where it
reads 507 against the registry as it stood before.

**The chapter page states the answer.** Every GigaViewer instance emits `<link rel="alternate"
type="application/atom+xml" href="https://HOST/atom/series/ID">`, so a chapter says which series it
belongs to in the platform's own numbering, and no title comparison is needed to establish it. 506
rows read that way through `adapters/gigaviewer/workaddress.py`. The last one is チャンピオンクロス,
which runs comici rather than GigaViewer and links `/series/<hash>`; `comici.series_link` reads it,
in the module that engine already has, because a second parser is where a fix fails to land.

**Two addresses, because the platforms differ.**

| | |
|---|---|
| `https://HOST/atom/series/ID` | the work's feed. Served by all eighteen GigaViewer hosts, so it is the one shape that reaches every row. |
| `https://HOST/series/ID/first_episode` | the work's reader address, and the link a platform puts behind a series on its own listings. 337 of the 506. |

一迅プラス, コミックガルド, MAGCOMI and webアクション serve no route for the second, which is 169
rows and 128 of them 一迅プラス. The first two answer it with HTTP 200 carrying their front page and
the words ページが見つかりません, so a status code decides nothing: the test that accepted an address
is whether the page it returned names the same series. That is how the soft 404 was found, and
without it 129 rows would have been attached to an address that does not exist.

**A title is the guard and not the evidence.** The series link already ties the address to the work,
so the og:title comparison exists to catch the other failure, a row whose `url` belongs to somebody
else. Every one of the 507 named its own work. The same comparison rejected Killer♡Twinkle on
チャンピオンクロス, where the platform writes a different heart character, which is the shape it is
there for.

**Two shapes outside the 507 had the same fault and are closed in the string.** ヤンマガWeb writes
`/comics/<work>/<32 hex>` and マンガワン writes `/manga/<work id>/chapter/<chapter id>` while serving
the work at `/title/<work id>`, so `identity.stable_url` now reduces both. That is 20 rows whose
anchor is the work's address rather than a chapter's. マンガワン's other shape, `/viewer/<chapter
id>`, holds no work id, and its 3 rows were closed by fetching: the viewer redirects and the page
states a canonical `/manga/<work id>/chapter/<chapter id>`.

**What build.py has to do, and it is the only thing left.** A row's `url` is still its newest
chapter's, so the anchor is still built from an address that moves. Everything above makes that
safe to change rather than changing it: the work-level addresses are attached, so the row can start
carrying one and nothing will be minted. What the row needs is a `series_url` field holding the
work-level address, which the release rows for カドコミ and COMIC FUZ already carry and no series row
does, and `identity.web_anchor` should prefer it over `url`. Either address above will resolve. The
feed address is the one to emit if a single shape is wanted, because it is the only one that exists
on every host; the reader address is better for the 337 where it exists and needs the capture to say
which those are.

**What was left alone, with numbers.** 2 rows on コミックノヴァ, `www.123hon.com/vw/<work>/<chapter>/`.
The work-level address is in the string, but `https://www.123hon.com/vw/nekomaho/` answers 403 to
this project's identity, so the reduction cannot be shown to lead anywhere and the rule was not
written. Nothing else in the corpus carries a chapter address: comicブースト's `/content/<work>0001`
is the work's own page and stays put across 81 chapters, and the remaining hosts address a work
directly.

### §21's fault: the row carries the address, and identity.py has the last move (2026-08-07)

`series_url` is emitted. **510 series rows carry one**, 341 the platform's reader address and 169
its feed, over 20 hosts. It is read from every capture under `data/queue/address-*.yaml` whose
`record_type` is `stable_address`, which is four files today and picks up the マンガワン and comici
rows the GigaViewer capture never covered. `address-moved.yaml` sits under the same prefix and is
skipped on its `record_type`, because what it attaches is another chapter address and that is the
one thing this field must never hold.

Nothing was minted. `identity.py` reports **3,155 identifiers, 0 new** and rewrites
`data/identity/works.yaml` byte for byte; `one row per identifier` and `rows with a moving address`
both stay at 0.

**The remaining move belongs to `adapters/identity.py`**, and it was left there because that module
was not this pass's to edit. Every call reading a row's address has to read the stable one:

```
web_anchor(w.get("series_url") or w.get("url"), w.get("work"), seen[...] > 1)
```

in `chain_joins`, in the `wanted` loop of the main pass, and in the `siblings` loop. The `seen`
counter that decides `shared` must count the same address the anchor is built from, or two works
sharing a container URL would be told apart by one field and merged by the other. No row is exposed
to that today: no `series_url` in the corpus is held by more than one row, and no row holding a
shared `url` has one.

**It was verified rather than assumed.** Resolving every row's `series_url` against the registry the
way `web_anchor` would gives 510 of 510 landing on the identifier the row already holds, 0
unresolved and 0 different. So the switch cannot mint and cannot move a work.

## 22. The work page cited a page the claim is not on (2026-08-07)

An operator followed a BOOK☆WALKER citation in *Sources of information*, found no 百合 anywhere on
the page it led to, and concluded the entry was wrong. They were reading the citation correctly.

**The evidence row named a shop and cited nothing.** `admitted_by` carries the comparator, the shelf
and the day it was read, and no address at all, so `credence.shelf_rows` had none to put on the row.
The nearest BOOK☆WALKER link on the page was the shop's own page for the book, which is `shop_url`
under *Sold at* and answers a different question. A citation that leads somewhere the claim is not
is worse than none: it invites a reader to check and then quietly fails them.

**The shelf is the address, because the shelf is where the filing is.** DEFINITIONS §2 admits the
work because a licensed retailer filed it under 百合, and only the shop's listing shows that filing.
`build.py:shelf_citations` reads it out of the captures' own `source_url`, and `cite_shelf` puts it
on the entry before `credence.py` builds the row.

| | |
|---|---|
| BOOK☆WALKER | **1,641 rows**, each citing the page of `tag/14/` it was read from, and carrying that page number as a field. Every one of the 1,644 records matched a captured page. |
| コミックシーモア | **296 rows**, citing `search/genre/37/`. The capture records no per-title page, so none is stated. |

**The capture header's claim was not leaned on.** `bookwalker-yuri.yaml` says the genre is
"presented on every work page", which would make the book's page a second place to check. It is a
statement about *work* pages, and 646 of the addresses we hold are *series* pages, which it never
covered. It is also a reading of a shop that redraws its pages at will. The shelf is cited because
it is where the capture read the claim, which is a fact about our own act rather than a prediction
about somebody's markup.

**The product page is still on the page**, on the print row as `shop_url` under its own heading, so
a reader gets the evidence and the shop separately and can tell which is which.

### `state_basis` was two facts welded into a sentence (2026-08-07)

"no chapter for 2 days in what we hold, but the platform still marks the serialisation as running"
is one claim about the world and one about this database, in a paragraph the page could only print
whole. It rendered as a dangling line under *Sources of information* while every other fact on the
page was a row.

Our half was already structured as `age_days`. The platform's half is now `state_claims`, in the
shape an evidence row has: who said it, what they said in their own word, when it was read, and
where. **270 works carry one**, 106 saying completed and 164 running, across カドコミ (`finished` /
`ongoing`), 竹コミ, キミコミ and six more (`完結` / `連載中`). `says` is our reading and `term` is
the platform's own value, kept apart so two sources agreeing does not read as one fact spelt twice.

`running_src` and `completed_src` now carry the platform's NAME instead of a sentence, so the prose
says which site said it: a work serialising in three places used to read "the platform" and leave
the reader to guess. **The prose stays.** `app.js` reads `state_basis` for the badge tooltip, and
the join is the point of that sentence: that the silence is ours rather than the work's is a
statement neither half makes alone.

**A bug fell out of it.** `completed_basis_ja` was read off `bucket`, the ingest loop's variable,
hundreds of lines after that loop ended, so every completed row was given the *last* bucket's
Japanese. It was invisible only because the sentence was a constant.

**What still needs prose**, and is not covered by any structured field: a short capture
(`N chapters are listed on the platform and we hold M`), a run of skipped slots, a hand review's
verdict either way, and a comparator's 完結 tag with the date it was seen. Each is a different kind
of statement and none is a source's claim about its own serialisation.

---

## 23. What the platform's silence was a fact about (2026-08-07)

§20 ran the corpus from a serialisation to the shop selling its collected volumes and reported that
"520 met a platform that lists no collected volume". That sentence is true and it is about the
**platform**. It was then read as a statement about the **work**, and the two are different things.

`w00537` コンカフェ嬢は恋を着る is the case that separates them. COMIC FUZ carries 31 chapters of it
and links to no shop at all, so §20 recorded it as a work with no collected volume. BOOK☆WALKER
sells three volumes of it under ＦＵＺコミックス and marks the series 完結. The volumes were there the
whole time; nobody had asked a shop.

**Every retailer route in this project was shelf-first.** `cmoa.py` enumerates コミックシーモア genre
37 and `bookwalker-yuri.yaml` enumerates BOOK☆WALKER tag 14, and each takes what is on the shelf.
The question neither could ask is "do you stock volumes for a work I already hold", and the
BOOK☆WALKER capture's own header already recorded what that costs: the 百合 tag is applied by hand,
コンカフェ嬢は恋を着る is not on it, and an absent tag says nothing about the work.

### Re-checking COMIC FUZ, on the work's own page

§20's entry read "volumes are sold inside the platform's own store and no page links out", which is
a conclusion about a platform drawn from a series page. A series page, a completed-series page and
a volume listing are different pages, so it was re-checked at `comic-fuz.com/manga/3455`, which is
this work.

The conclusion holds and the reason is stronger than "no link was found". FUZ serves its whole page
model in `__NEXT_DATA__`, and for a manga that model has fields for the chapters, the authorships,
the tags, the manga itself and the share link. It has no field for a book. So no page kind of a
series can carry a shop link, because the data behind every one of them is the same document.
`/books` and `/book/<id>` are FUZ's own digital store, rendered client-side, and state no ISBN.
`engines.py` now records that rather than the weaker claim.

### The shop that will answer, and the shop that would have answered better

コミックシーモア states an ISBN on 618 of its 1,833 shelf works and is the shop this route wanted.
It is closed to us. `https://www.cmoa.jp/robots.txt` carries `Disallow: /search/result/` under
`User-agent: *`, and that is exactly the endpoint `cmoa.shelf_url()` builds, so the keyword search
is not available whatever it would have answered. **The existing shelf capture reads that endpoint**
and predates anyone reading the file; it is recorded here and the decision about it belongs to the
project owner, as the same question did for NDL's `/api` in §9.

BOOK☆WALKER's robots.txt closes `/ex/problem/`, `/entry-list/`, `/member/`, `/history/delete/`,
`/history/parts/`, `/prx/ma/` and sample links, and `/search/` is not among them. `bookwalker.py`
has read it for completion markers since before this. So the permitted shop is the one that states
no ISBN, and the join had to be made another way.

### Two agreements, by two parties who did not consult each other

`adapters/shopquery/` asks the shop for the author's name first, because an author search that
comes back with an agreeing title has agreed on two fields at once. `adapters/madb/by_shop_query.py`
then asks the national bibliography, joining on the title and requiring a person to agree, which is
`by_title.py`'s rule and not a second copy of it.

A hit whose title agrees and whose credit does not is **recorded and joined to nothing**. There are
**77 such candidate rows over 16 works** in `data/queue/shop-query-title-only.yaml`, each carrying
both credits so the question can be settled by looking. トワ・エ・モア is why: a 1996 コンパス
anthology and a 2024 講談社 series share that title, and a wrong join is hard to see afterwards.

### The measurement, before and after

**645 web works had no print edition. 564 do.** Both counted the same way, as a row in
`data/build/series.json` carrying `sources` and no `print`, which is `editions/capture.gap_works`.

639 of the 645 carried an address the capture could put to the shop.

| The shop's answer | Works |
|---|---|
| stocks a title this database recognises, and agrees on a creator | 158 |
| stocks a title that agrees, and no person does | 16 |
| answered, and stocks nothing under a name this database recognises | 426 |
| answered nothing at all, on every query | 39 |

So **at least 174 of 639, better than a quarter, had shop stock their own platform never mentioned.**
That share is the answer to what §20's 520 was a fact about.

Of the 158 the shop and this database agree about, 89 reached a bibliography record and **87 new
work records were written**, with 9 more already held by another route. The 69 that reached nothing
split on a field the shop states and nobody had been reading:

- **32 whose hit carries 底本発行日**, the publication date of the print edition the file was made
  from. A printed book exists and MADB 1.2.18 has not catalogued it.
- **37 whose hit carries none.** A digital-only edition, so there is no print run for any
  bibliography to hold, and asking again will not change that.

### What the residual is now

| | Works |
|---|---|
| the shop answered and stocks nothing under this name | 432 |
| the shop stocks it and agrees on a creator, and the bibliography holds no record | 77 |
| the shop answered nothing at all | 39 |
| a candidate matched on the title alone, deliberately not joined | 16 |

The 77 divide 37 printed against 40 digital-only, on the same 底本発行日 test. So of the 564 left,
**37 are books that exist and are not yet in the national bibliography**, and the rest is either a
work with no print edition or a work the shop does not stock under a name we know it by.

### Why a BOOK☆WALKER shelf hit produces no print record, which is a separate fault

It was suggested that コンカフェ嬢は恋を着る is on the 百合 shelf and failed to join. It is not on
that shelf: the only occurrence of the title in `bookwalker-yuri.yaml` is the header sentence
saying it is absent. The fault behind the suggestion is real and larger than one work.

**BOOK☆WALKER states no ISBN, on any volume.** `bookwalker-volumes.yaml` records it in its own
header and its counts agree: `volumes_with_isbn: 0` across 5,968 volumes read from 2,423 works.
Every route this project has from a shop to a bibliographic record is keyed on an ISBN, so no
BOOK☆WALKER row can reach one, and `bwingest.py` builds a record from the shop's own listing
instead. That is not a join failure on one work; it is the shape of the shop, and it is why this
route joins on a title and a person and why the 96 joins it produced carry that as their basis.

### The nine the registry refused, and they are worth a look

`identity.py --attachments` applied 87 of 96 joins and refused 9, each because the bibliography
record is already held by another work identifier. Attaching it to a second one would say the two
are one work, which is a merge and needs `--merge` with a basis. Every one of the nine is a print
record that entered by another route and a serialisation that entered separately, so they are
candidates for exactly that decision and none of them was taken here.

### Where §20's other 47 went

47 works had a platform that DID state an ISBN and still carry no print edition, which is a
different failure from the one above and worth separating. Of the 54 addresses behind them, **37
ISBNs are not in MADB 1.2.18 at all**, 3 were refused because the bibliography says the number
names another book, and the remaining 14 have a record written that no identifier attaches to their
serialisation. The first group is the release lagging, the second is `by_platform_isbn.agreement`
working, and only the third is anything to fix.

## 24. The publisher names that resisted (2026-08-07)

272 publisher and imprint names showed in Japanese in English-only mode when this round started,
on 2,124 volume rows. 240 of them now carry an English name and 32 do not. Each of the 32 is
below with what was read. The rule they were measured against is NAMES-PLAN §6: an unsourced
name shows the Japanese, which a reader can search, and a wrong Latin name is worse than that.

Two bases were used for the 240. `official-jp` means the company signs itself in Latin letters
somewhere on its own site and the entry carries that page. `romaji` is ours: nothing publishes a
Latin form, so the note says what was read and how the name was put together. A katakana label
almost always spells a foreign word, so the source word is the answer and a syllable-by-syllable
pass is not. A kanji label was romanised only where every part is a word with a single reading,
which is why several below are absent from that set.

### The label with the most rows behind it

**百合コレ**, 496 volume rows, which is 82 per cent of everything still unnamed. ナンバーナイン's own site
at no9.co.jp and its corporate site at corp.no9.co.jp publish no label list. Its press release
announcing the company's move into paper names two labels, No.9 Comics and Blend Comics, and
this is neither. BOOK☆WALKER files it at bookwalker.jp/label/11249 with the Japanese alone. コレ
is a truncation and nothing states what it truncates, so Yuri Kore and Yuri Collection would
both be ours to invent. It is the one entry here where a single source page would pay for
itself.

### Two classes, and one line each for the rest

**A person in the publisher field.** A person's name in the publisher field: the artist self-
publishes and the distributor files them as the publisher. A person is not a company, and the
reading of a pen name is not something to guess. The names:
嵩乃朔、山名沢湖、河津ケント、とばり湊、雪尾ゆき、赤月めう、新居さとし、高橋真弥、夢乃むえ、川村マユ見、さとうメメ子、朱村咲、珠虫さとり、あおい華葉、井庭人.

**A circle name in kanji nobody has read aloud in print.** A circle name in kanji whose reading
nothing states. §6 forbids romanising kanji by guessing a reading, and each of these has more
than one defensible one. The names: 空色の音、赤紅、黒戌舎、空想舩、狗古堂、踏月、口達者同盟、わんこ院.

**デジコレ.** 小学館's label. A truncation with nothing stating what it truncates, so a romanisation
would spell a word nobody uses and an expansion would be a guess.

**デジコレ　マカロン.** The マカロン strand of デジコレ, unresolved for the same reason.

**青騎士.** KADOKAWA's magazine. The kanji reads あおきし or せいきし and KADOKAWA's own label list prints
neither, so romanising it would pick one.

**青騎士コミックス.** The book line of 青騎士, unresolved for the same reason.

**じるみて.** forcs's label. A kana coinage we could find no site for; it is left as it is rather
than romanised into a string with no owner.

**GP-KIDS/高菜しんの.** Not a publisher name. It is an imprint beside a person, catalogued in the
publisher field, and it is the exact shape that makes MADB's parallel titles unsafe to read as
translations.

**スタジオぷち屋 桜那えいか、.** A circle name with an author's name and a trailing comma catalogued into one
publisher field. The string is a record artefact, not a name.

**詳伝社.** One volume. 詳伝社 is not a house we can find; 祥伝社 is, and it is already curated as
Shodensha Publishing. This looks like a catalogued character error and naming it would publish
our guess about which house it is.

**フェアベル.** The company's site at fairbell.co.jp is a parked domain now and we found no page of
its own. フェアベル reads as the German fair Bell or the English fair bell and nothing states which.

## 25. The work that was asked for and not got (2026-08-07)

ぬるめた is one of 47 works `data/source/comicfuz/resolved.yaml` names and the only one absent from
the capture. Its confirmed address is `https://comic-fuz.com/series/2389`, the one row in that file
spelled `/series/` and not `/manga/`, because that is what the search returned.

`adapters/comicfuz/releases.py` has rewritten `/series/` to `/manga/` since `2588a34`, and the
rewrite ran. What it did not do was reach the fetch. The rewritten address decided whether the row
was a FUZ target and keyed the set that removes duplicates, and then the untouched row was appended
to the target list, so `fetch()` asked for `/series/2389`. That address answers 404. `/manga/2389`
answers 200 and its `__NEXT_DATA__` holds 75 chapters under こかむも. Both were checked on
2026-08-07, and the 404 is also in `96ab183`'s message from 2026-08-02, recorded there as a fact
about the platform when it was a fact about the adapter.

**Neither offered cause was it.** The `--gap` file was not stale: 36 of the 47 confirmed works
reach the target list from `resolved.yaml` alone and every one of them was captured. The fetch did
fail, and that is where the work was lost rather than where it went wrong.

**What the miss left behind, which is the part worth keeping.** Nothing. Every capture pass here
collects its failures in a local list, prints them after the run and exits zero, so the only
evidence was a line in a terminal. The capture was written with 46 of 47 works and reported
success, `works_resolved` in its header counted the rows underneath it and agreed, and no number
anywhere in the repository said a work had been asked for and not got. That is REQUIREMENTS §4 and
STANDING-INSTRUCTIONS §13 in one place: absence looked exactly like a work nobody had named.

**The measure.** `adapters/capturegap.py` joins each pass's target lists against its captures on
the platform's own identifier, and `targets a capture wrote no row for` is the budget. It reads
neither the `failed` list nor any counter a pass prints, because both are computed from the rows
the capture wrote and agree with it by construction (§14b). It also declines to reuse the adapter's
address handling, which is the code that failed; the pattern in `capturegap.py` accepts both
spellings of a FUZ address directly, which is why it can see this at all.

**It found four more, all on ニコニコ漫画** and none on カドコミ. 将来的に死んでくれ (31151),
打撃系鬼っ娘が征く配信道!@COMIC (49417), ミモザの柩 (54233) and てあとるりりぃ (61505) are named
by `data/coverage/webcomics-works.yaml` with a `/comic/<id>` address each, and neither ニコニコ pass
holds a row for any of them. Their cause is not the FUZ one. Each answers **200 with a 9.7 KB shell
carrying no `meta_info`**, where a work the platform still serves renders around 200 KB, so the
platform is saying it no longer has these and saying it with a success code. The pass reads that as
"no meta_info date" and drops it in the same silent way.

So the budget starts at 5. One of those falls when the fixed FUZ pass next runs. The other four
fall when a withdrawn work is written into a register the count reads, the way
`data/source/kadokomi/withheld.yaml` already accounts for the five works カドコミ serves and this
project refuses.

## Contested anchors, and what was decided

One print record claimed by two identifiers is not by itself a merge. It is evidence that the two
are versions of one story, and the tool refuses to attach it to both without a stated basis, which
is right: retiring an identifier is not reversible for anyone holding a link.

Four were merged on 2026-08-07. 超深宇宙より愛をこめて【読み切り版】, 白妙様、秘密ですよ／読切版 and
転生王女と天才令嬢の魔法革命【タテスク】 each name an edition in the title itself, and DEFINITIONS
records that the test binds the work and not the edition. 飛野さんのバカ was held twice under one
title with one author and one print record answering for both.

**両片想いな双子姉妹 and 百合百景 stay separate.** はちこ wrote both. They are two serialisations,
of 35 and 82 chapters, that share a single print record, which reads as one volume collecting an
author's short work and not as one story catalogued twice. Merging would retire an identifier on
the strength of a shared binding. They are recorded as related and the reader sees both.

**リリウム・テラリウム is unresolved and should not be left so.** w01168 holds the title with its
ISBD punctuation still attached, so it does not match w01495, which holds the same title clean.
The comparison that would settle it cannot be made until the title is parsed, and that fix is in
hand. Once the string is split, revisit rather than assume: the parallel title names an omnibus,
and an omnibus of a work is an edition of it.

## 25. The 32 that resisted, and what the second round did with them (2026-08-07)

§24 left 32 publisher and imprint names with no English, on 595 field occurrences across 550 print
rows. All 32 render in English now. Five of them were found rather than romanised, one was proved
to be a different company under a catalogued character error, and the rest carry a romanisation
marked as ours. This entry records where the five were, because each was missed in a way that will
recur, and what was searched for the rest, because that is what makes the fallback a last resort
rather than a shortcut.

### The five a second look reached

**フェアベル → Fairbell.** The first round read fairbell.co.jp, found a parked domain, and stopped.
The company's live sites are fairbell.jp and fairbell.net, and its bookshop signs itself
© FAIRBELL Co.,LTD. **A parked domain is evidence about a domain, not about a company.**

**じるみて → jilmitte.** forcs addresses the label at forcs-comic.jp/jilmitte and its editorial
account is @jilmitte. **A label's own address carries its Latin spelling even when no page prints
it as text**, which is the shape a text search does not find.

**デジコレ → Digicolle.** 小学館's own e-comic store addresses it at
e-comi.shogakukan.co.jp/digicolle, carries logo-digicolle.svg, and prints the lockup
デジコレ DIGITAL COMICS. The first round looked at the corporate site, where the label is filed
under its full name デジタルコミックコレクション and the truncation never appears. **The store is a
different publication from the company site**, and a label lives in the store.

**詳伝社 → Shodensha Publishing.** Not a house at all. The single record is Free soul by
やまじえびね, ISBN 4396763387, and the 4396 prefix is 祥伝社's: openBD answers 祥伝社 for other
ISBNs carrying it, and the book is a FEEL COMICS volume out of 祥伝社's FEEL YOUNG. The first round
suspected the character error and declined to act on a suspicion, which was right; **an ISBN prefix
turns the suspicion into an identification** without asking anyone to guess. The Japanese stays as
catalogued, because the source layer records what the source said.

**青騎士コミックス → Aokishi Comics.** KADOKAWA's product pages print no Latin form, which is where
the first round stopped. The magazine publishes at note.com/aokishi and posts as @aokishimanga, so
あおきし is the publisher's own answer and せいきし is out. The Latin spelling is still ours, so it
is filed as a romanisation. **A magazine has a publication of its own, separate from its
publisher's catalogue.**

### 百合コレ, which is 496 of the 595 and was searched again

ナンバーナイン's yuri label. no9.co.jp publishes no label list; the company's note account
documents Blend and nothing else; its press releases name No.9 Comics and Blend Comics and neither
is this; the label page at bookwalker.jp/label/11249 carries the Japanese alone with no Latin
anywhere on it, in the heading, the breadcrumb, the description or the logo. Nothing states what
コレ truncates.

So it is spelled out and not expanded: **Yuri Kore**, marked as a romanisation. Yuri Collection
would publish a name the label does not use, and the store settled that shape already when カドコミ
was recorded as Kadokomi. What is not in doubt is the reading, so the entry carries it as
researched and the row does not tell a reader the pronunciation is uncertain when it is not.

### What the residue is, and why romanising it is the answer rather than a queue

The remaining 25 are self-publishing: 13 are people the name store already holds, because a work
published through a shop's individual-publishing service names its own author as its publisher, and
the rest are one-person circles. Searched: each circle name against its artist, against pixiv and
BOOTH, and against the shop listing the books. 空色の音's books carry a signature reading
`sora amakaze` in the blurb, which is the artist signing a description rather than the circle
naming itself in Latin, so it is recorded here and not used. 赤紅 is 秋月ルコ's circle and とばり湊
is こよぬい's, both confirmed and neither spelt in Latin anywhere. The others return nothing at all.

These are not a backlog. NAMES-PLAN §4a says so directly: a circle with no tankōbon, no database
entry and no English-language presence has no Latin name to find, and a marked romanisation is a
finished state. What would change it is a sighting, and the store overwrites on one.

### Two strings that are records rather than names

**GP-KIDS/高菜しんの** and **スタジオぷち屋 桜那えいか、** are an imprint and a person catalogued into
one publisher field, the second with the trailing comma of a truncated list still on it. They
romanise as what they are, `GP - KIDS / Takana Shin no` and
`Sutajio Puchiya Sakurana e Ika,`, and both read as the artefacts they are. One row each. Stripping
a trailing comma is a rule with counter-cases and worth writing only when a second case turns up;
this is recorded so that the second case is recognised as one.

### The name that was missing from the map, and how it was found

Written up because the finding is about the measure and not about the name. Every count of unnamed
publishers in this repository, including the one at the top of §24, was derived from the same
census of the corpus. Normalising the corpus the way `app.js` does instead, and then asking the
shipped map for what came back, found a name the map did not hold: **高菜しんの**.

`GP-KIDS/高菜しんの` is catalogued in the publisher field AND the imprint field, and the two
normalise differently, because the slash separates an imprint from a person. The census keyed its
slots on the catalogued string alone, so whichever field was read first decided what the shown name
was, and the imprint's name never entered the map. §14b, exactly: **the measure was blind in
precisely the place the producer was blind**, and it took a measure that owed the producer nothing
to see it.

Two faults, one string. The census now keys on the field as well, and the map is written in two
passes so a raw catalogued string may fill a gap but never displace a name: writing each slot's two
keys as it went let the imprint's rendering claim the publisher's own key, so the publisher rendered
as the person inside it.

`publisher keys the interface misses` is the measure, kept as a budget at 0. It carries a
transcription of `publisherOf` and `imprintOf` from `app.js`, which is a third copy of a rule on
purpose: it is a copy of the CONSUMER, and it is the only thing in the tree that can observe the two
implementations disagreeing. Both modules had written down that the risk exists and that the
double keying guards it. The double keying is a mitigation and was never a check.

### What was tightened

`publishers with no English` reaches 0 and now measures the SHIPPED map rather than re-running the
producer's own join, which is §14b: the old measure could not see a name the build had failed to
write, and could not see a romanisation at all, because the store holds a reading and only the
build spells it.

`names rendered two ways` is new, at 2. It counts strings the shipped maps spell one way as a
publisher and another way as a person. Both entries in it predate this round: ガレットワークス is
`Galette Works` beside its books and `Garettowākusu` beside its name, and ネジ式１３番地 is
`Nejishiki 13-banchi` and `Neji Shiki Ichisan Banchi`. **The fix belongs on the author side.**
Each is a circle whose publisher entry is the better answer and whose person record has never been
told so.

## 26. The readings under the romanisations (2026-08-08)

§25 took `publishers with no English` to zero, and it did it largely by romanising. That finished
the rendering and moved the sourcing: a romanisation is the reading spelt in Latin, so 254 of the
323 shipped publisher keys were a Latin form of ours and **134 of them stood on a reading no source
states**, each carrying the mark that says so and none carrying a `reading_basis` at all. Nothing
counted them. The first budget's fall to zero read as the work being finished, which is
STANDING-INSTRUCTIONS §13 in a number rather than in a file.

107 are settled here and the count is **21**. `publisher readings nobody has settled` is the budget,
new at 134 and ratcheted to 21 in the same run, and it reads the SHIPPED map and asks for the mark:
an earlier attempt emptied this class by suppressing the mark in list views and was rejected, so the
measure is built where that would show as a fall nobody earned.

### Where the 107 came from

53 came from the National Diet Library, which files a publisher transcription beside the label on
its `/books/` records, in katakana on some and as a transliteration of the kana on others.
`ndlsearch.ndl.go.jp/robots.txt` disallows `/api` and that route stays closed; the record pages are
open, and they answer. They rate-limit hard, returning 503 to anything faster than one page every
few seconds, which is why the sweep took two hours for 124 labels and why only 61 of the 134 came
back with an answer at all.

Four came from a house stating the reading of its own name. 宙出版 titles its front page
宙（おおぞら）出版のHP。, which is a furigana gloss the company put there itself; xfolio.jp titles
itself Xfolio（クロスフォリオ); bookman.co.jp spells the katakana half of ブックマン社; and 一ノらい's
circle らいおん小屋 publishes at liongoyaithinoli.wixsite.com.

The remaining 50 were settled here, each with a note saying what was weighed. They are the labels
made of loanwords and everyday compounds, where every element has one reading: 別冊 is ベッサツ,
女子部 is ジョシブ, 出版 is シュッパン, and there is no competing candidate to weigh them against.

### Three names the round found were already wrong

路草COMICS was published as Rosou COMICS and is Michikusa COMICS. §25 recorded that the magazine's
own site did not resolve and read the two characters on their on readings. It publishes at
michikusacomics.jp, and the National Diet Library files the label Michikusa komikkusu
independently. **A magazine that could not be found is not a magazine with no address.**

らいおん小屋 was Lion Koya and is Lion Goya. 小屋 standing alone is こや and voices to ごや after a
modifier, as it does in 犬小屋 and 山小屋, and nothing mechanical decides which. The circle's own
site at liongoyaithinoli.wixsite.com spells it liongoya.

わんこ院 was one of the eight circle names §24 left unread, on the ground that 院 after a kana word
has more than one defensible reading. The National Diet Library holds a volume the circle issued
and files the publisher Wankoin. The analyser had guessed the same string, which is the answer
rather than a coincidence: what was missing was never the reading, only something able to state it.

### What the catalogue settled that no rule would have

Letters in a comics label were the largest single question, and the tempting rule is that an
initialism is said letter by letter. The catalogue holds the counter-case. It files
HCヒーローズコミックス as エイチシー and KCデラックス as ケーシー, and then files あすかコミックスDX
as アスカコミックスデラックス and UPコミック as アップコミック, because those letters spell a word.
`KCDX. 週刊少年マガジン` comes back ケーシーディーエックス, so the same two letters go both ways in
one house. A rule applied across the set would have been wrong four times; asking per label was not
avoidable work.

Where the catalogue leaves a Latin run as it found it, so does this: サンデーGXコミックス comes back
`Sande GX komikkusu` and マンガBANGコミックス comes back `Manga bang komikkusu`. Those readings carry
the letters through, and the note says nothing states how they are spoken and that the Latin
rendering does not turn on the answer.

### The 21 that resist, and why

Twelve are people, and they heal from the author side: あおい華葉、さとうメメ子、とばり湊、井庭人、
夢乃むえ、川村マユ見、河津ケント、珠虫さとり、赤月めう、雪尾ゆき、高橋真弥、高菜しんの. A work
self-published through a shop's individual-publishing service names its own author as its
publisher, and `publishers.english` consumes the author store for exactly that, so settling the
person settles this. **Do not settle them here**, because two producers of one fact is what
`names rendered two ways` already counts. The National Diet Library answered one of them in
passing, filing 川村マユ見 as カワムラ マユミ at
`ndlsearch.ndl.go.jp/books/R100000001-I01211008001685179`.

Seven are circle names in kanji nobody has read aloud in print: 空色の音、赤紅、黒戌舎、空想舩、
狗古堂、踏月、口達者同盟. Each was searched against the artist, against the National Diet Library and
against the shop listing the books. None of the seven is in the national collection, which is what
made わんこ院 different, and a circle with no book in a catalogue and no Latin anywhere has nothing
left to ask.

Two are records rather than names: `GP-KIDS/高菜しんの` and `スタジオぷち屋 桜那えいか、`, an imprint
beside a person and a circle beside an author with the trailing comma of a truncated list still
attached. §25 recorded both. A reading for either would be a reading of a catalogue line.

## Task: search the unsettled names one at a time

Recorded 2026-08-08 for the owner to start later. It is written down rather than started because
it is slow by nature and cannot be hurried: the value is in asking about one name properly, and a
sweep is what produced the residue.

**The populations.** 271 credited authors and 16 publishers still render as a romanisation whose
reading nothing states. 117 of the 271 have never been put to the National Diet Library at all: the
round that settled 460 of them found まんが王国 answered in bulk and made four NDL requests in a
whole session, which was the right economics for the bulk and left the residue untried on the
strongest route.

**Why one at a time.** Every name settled by hand this session broke a pattern rather than
following one. 華葉 is カバ, where the characters predict カヨウ and the store had assembled ハナハ.
路草 is みちくさ, where a previous round searched for the site and recorded it as not resolving.
らいおん小屋 is ごや, not こや. 158 of 418 shop-sourced readings contradicted the analyser outright.
A rule that fits the first ten of these will be wrong about the eleventh.

**What is already known, so it is not redone.**

- Misses are recorded. `data/names/attempts.yaml` holds them per name and source, and a route that
  asks should write there so the next pass skips what has been answered. 328 まんが王国 misses are
  already written off. Only a real answer counts: a 503 is the server refusing.
- NDL rate-limits to roughly one page every few seconds and the `/books/` record pages carry
  タイトルよみ and 著者標目. `/api` stays closed by robots. Pages cache to `ndl-cache` by default now.
- NDL's conventions are not verbatim truth: 私 defaults to ワタクシ, を to オ, ○○ to マルマル, and an
  English subtitle is sometimes spelled out in katakana. Roughly a third need a reviewer's judgement.
- Seven of the publishers are doujin circles in kanji that are in no national collection, which is
  what made わんこ院 settleable and these not. Six are people whose author record heals them.
  とばり湊 and 井庭人 are in `publishers.yaml`, in no author record and in no corpus credit, so
  nothing on the author side can reach them and they need a decision instead of a search.

**Some of it is not a sourcing problem at all**, and that part is worth doing first because it needs
no network. `あんじんねこ@創作` carries a handle suffix that is not part of a name. `お久しぶり` is a
set phrase split as though お were an honorific. `2C=がろあ` and `R-指定` have punctuation spaced
apart inside a pen name. `○山浩平` masks a character the way `白百合に×いを込めて` does, and the same
disposition is available: no reading can be recorded, and the rendering should still not be
`○ Yama Kōhei`.

**One constraint that will recur.** For some artists the attestation sits in works §7 excludes. The
reading of a person's name is not itself excluded material and belongs here, but a citation is a
link, so record the basis and the reasoning and do not address it. あおい華葉 is the worked example.

## Digital delivery dates are accepted where no paper record is reachable (2026-08-08)

**The owner's ruling, which reverses part of an earlier one.** Where no accessible record of a paper
version exists, the date a shop began delivering the digital edition is accepted as the best
available, with its source recorded as any other date is. Flagged here as data to follow up, because
it is the weakest date the database carries and a better one may appear.

**What it overrides, and what it does not.** `adapters/cmoa_volumes.py` measured 配信開始日 against a
print date on 353 volumes and found 154 delivered before print and 45 more than three years after,
the extreme being 128 months. That finding stands wherever a print date exists: there the print date
wins and the delivery date is not evidence about it. What is overridden is the digital-only case,
which the module also refused on the grounds that cmoa's blurb for #ミカちゃんともなちゃん states the
file is the ebook edition of a 同人誌, so an earlier publication exists without being dated. That
argument is sound and the owner's judgement is that a dated row a reader can act on beats an
undated one, provided the basis says what it rests on.

**The population.** 1,209 of 1,833 cmoa works read `first_publication_basis:
shop-delivery-date-only` with `first_publication_date` null. 1,347 works in the corpus carry no first
date at all and 1,308 of those have a print block naming a shop. BOOK☆WALKER states no ISBN on any
of 5,968 volumes read, so an ISBN-keyed route cannot reach its rows; 真夜中だけのおともだち is the
example the owner raised, a single volume self-published through BOOK☆WALKER with no date anywhere.

**The date was not kept.** The capture recorded the basis and discarded the value, because the ruling
at the time said it was unusable. So this is a recovery from `cmoa-cache` and the BOOK☆WALKER
captures rather than a new fetch, and it should stay that way: the pages are already on disk.

**What a reader must be able to tell.** A delivery date is not a publication date and the interface
should not present it as one. It needs its own basis in the store and its own words on the page, in
the same way 発売日 and 奥付 are two facts about one book rather than one fact at two precisions.

### What the recovery found (2026-08-08)

**The value had not been thrown away, only ignored.** Every one of the 1,209 cmoa rows carried
`delivered` on its volumes and every one of them was day-precise, so `adapters/cmoa_volumes.py
--delivery` dated all 1,209 with no network at all. BOOK☆WALKER was the same story one layer up:
`bwingest.py` had been writing `delivered` into every source record it made, so the corpus dates came
out of `data/source/bookwalker/` and not out of a fetch either. Nothing in this round cost a request.
真夜中だけのおともだち reads `delivered: "2018-10-20"` and has done since 2026-08-05.

**The population, reproduced and one figure corrected.** 1,209 cmoa rows and 1,347 undated works-list
rows are both exact. What the brief did not say is that the 1,308 print blocks naming a shop name
BOOK☆WALKER on every single one of them: cmoa's shop address reaches a record only through
`marketing_label_basis`, which is BOOK☆WALKER's alone, so the two shops contribute to different
halves of this problem. cmoa's digital-only rows are not in the corpus at all, because that route
enters through the ISBN and these have none, so dating them prepares a promotion rather than changing
a page. 1,297 of the 1,347 corpus rows had a delivery date recoverable from disk; 1,084 works-list
rows now carry one, and 12 works in the whole corpus still have no date of any kind.

**Two counts of 1,209, which are not the same 1,209.** cmoa has 1,209 rows basised
`shop-delivery-date-only` and BOOK☆WALKER has 1,209 undated source records. The coincidence is worth
writing down because it invites the reading that one file is a view of the other.

**What the shop says about an earlier edition, counted.** Over the 1,971 cached cmoa work pages, a
doujin word appears somewhere on 321 and inside the shop's own description box on 284. Of those the
shop states the file is the electronic edition of something published earlier on 174, and states the
file is itself a doujinshi on 79. The remaining 31 use the word in a plot summary, and telling those
apart is the whole difficulty: `同人誌風マンガ` is a commercial book in the style of one,
`コミティアの人気作家` describes the author, and `参加した同人誌即売会で` is a scene.
`adapters/test_delivery.py` pins all three as refusals.

Neither of the first two figures withholds a date, and that is the change DEFINITIONS §6 made on the
same day. A stated earlier edition does not imply a stated earlier DATE, so the 174 are recorded
because a reader should be able to see the shop said so, and not as an argument.

**The follow-up measure, and the honest limit on it.** `first_publication_followup` sorts these rows
and only one of its states is work anybody could do. `no-earlier-record-expected` is finished, because
the shop says the file is a doujinshi and §6 says the delivery day may be the only datable event it
has. `earlier-edition-unsourced` is a row a better source could answer. `unclassified` means the shop
said nothing about the edition, so the row is evidence for neither of the other two.

The split works on cmoa, where 79 are settled and 165 open. It barely works on BOOK☆WALKER, where
1,065 of 1,084 published rows read `unclassified`, because that shop's descriptions are not held
offline and the only signal available is the publisher field: 19 rows record the author as her own
publisher, which is the shop's individual-publishing route describing itself. So `status.html`
publishes the total and not the split, since a follow-up figure of 0 beside 1,084 rows would read as
nothing to do when it means nobody has read the descriptions.

No doujinshi distributed only at an event was seen. Every row here arrived through a shop's own
shelf, which is what DEFINITIONS §6 says admits it, so the out-of-scope case did not arise and there
is no count to report.

**Where the delivery date is allowed to go, and where it is not.** `delivery.promote` refuses on sight
where any volume of the work states a printing, which preserves the 353-volume measurement whole. The
date reaches a reader as `first_publication.date` with `date_event: shop-delivery` beside it, and it
never reaches `print[].first`, which the interface labels 初刊. It travels there as `delivered_from`
instead, so 1,140 works are not described as printed editions with a date no printer set. `first date
precedes its editions` reads the printing and cannot see the delivery date, deliberately: 154 of the
353 volumes were delivered before the printing, so reading it there would report the commonest case in
the shop's catalogue as a contradiction. `a delivery date never stands beside a printing` is the
invariant that covers these rows instead.

**What the interface still needs, which is not built here.** `kari/app.js` labels the works page date
刊行 and the catalogue panel 初出, and both now sometimes hold a delivery date. The build carries
`first_event`, `print[].delivered_from` and a `delivery-date` row in the work page's other-data table,
so the change is a label switching on a field that is already there rather than new plumbing:
配信開始 / Delivered from where `first_event` is `shop-delivery`, the same wording on the volumes line
where `delivered_from` is set, and an `EV_HOLDS` entry so the source row reads 配信開始日 instead of
the raw key.
## What the credit pages still need (2026-08-08)

The two preparatory steps on the author side are done: the duplicated credits are merged and every
credit the works list names holds an identifier. Nothing renders yet, and this is what stands between
the registry and a page a reader can open.

**Nothing serves a credit page, so nothing serves a retired credit id either.**
`adapters/credit_identity.forwarders` produces the same stub 49 retired work ids serve today, with
`rel=canonical`, `noindex,nofollow`, a meta refresh, a `location.replace` and a sentence naming the
successor. It is tested and it is deliberately NOT wired into `deploy.sh`, because a forwarder
pointing at `credit/c00554/` would send a reader to a page that does not exist. Wire it in the commit
that ships the page, and not before.

**The interface holds no map from a credit to its identifier.** `feed/names.json` is keyed by the
folded credit string and carries the reading, the romanisations and the ruby; it carries no id. So
`app.js` can render a credit and cannot link it. The smallest change that closes this is an `id` on
each entry of the `authors` map, taken from the registry by the same fold the anchors use. That is a
change to `build.py` and to the reader interface, and the reader-facing part is the owner's to make.

**The address is spelt `credit/<id>/` today and the word is provisional.** `author/` would be wrong
for the 20 credits that are not people, and the identifier is opaque, so the directory carries no
claim. Nothing is published, so changing it costs nothing now and costs a redirect later.

**The one-work case is the common case.** 1,504 of the 2,232 credits carrying an edge are named on
exactly one work, and a page holding one row has to be worth opening. The owner has ruled that every
author gets an address regardless, so the question is what else belongs on it: the reading and its
basis, the publishers behind the works, and the relations recorded under `homophones`.

**The role is on the edge and the corpus almost never states it.** 14 of 4,350 edges name one.
`inputs.split_credits_detail` reads the label off the same traversal that finds the name, so
`原作／宮澤伊織　作画／水野英多` yields both people with their jobs. The problem is upstream: the
works list is written with the notation already taken off, so 3,076 of its 3,077 rows say nobody's
job, and the labels reaching the registry all come from release rows, of which 196 of 805 carry a
work identifier to hang an edge on. A page wanting to say who drew and who wrote needs the works list
to keep the field the platform sent, which is a change to how `series.json` composes its author.

**Seven pairs of credits share a reading and are held apart**, recorded in the registry's
`homophones` list with the reason for each. A page for either should be able to say that the other
exists, which is what the owner's ruling means by information hung beside a credit. Nothing renders
that yet, and 須藤佑実 against 須藤祐美 is the one a source check should settle first: both are
girls×garden comics books from ジーオーティー and both sit in the Avalon anthology line, which is the
shape of one artist mis-keyed at one source rather than two artists.

**A credit joined by an ampersand is one identifier for two people.** `iimAn&惟丞` and
`大島永遠&大島智` are single credits in the corpus because no splitter divides on `&`;
`names.credits` unescapes `&amp;` and says in its own comment that the second is two people.
Splitting there is a change to `inputs.SEPARATORS`, so it wants the same care the interpunct
argument got, and until it happens two pages are one.

**Two credits are two people separated by nothing but a space**, from release rows: `狗之餌 廃狼`
and `織日ちひろ 虫原`. A space is not a separator anywhere in the splitter, on purpose, because
森島 明子 and 高坂 はしやん are single people written that way. Neither string mints an identifier
today, since identifiers come from the works list, and both are counted by `credit fields an
identifier does not cover`.

**`とばり湊` and `井庭人` are in `data/names/publishers.yaml`, in no author record, and in no corpus
credit at all.** Found while measuring the credit population and left alone: the publisher side is
somebody else's pass.

**The store still holds the second spellings the registry now merges.** 72 records in
`data/names/authors.yaml` are a credit written beside its own reading, and they ship in
`feed/names.json`, which is where the 82 shared readings were measured. The registry answers for them
through an attached anchor, so nothing is lost, and a later pass that wants the name store to hold
one record per credit can read the rulings file to do it.

### The credit and publisher pages, and what closing them left open (2026-08-08)

Everything under "What the credit pages still need" above is done except where this section says
otherwise. `adapters/pages.py` serves 2,241 credit pages and 164 publisher pages with a forwarder
for every retired identifier of either kind, `feed/names.json` carries the identifier on each name
so the interface can link one, and `data/identity/publishers.yaml` holds 164 house identifiers
minted under the one-namespace ruling. What follows is what is still owed.

**275 of the 320 imprint lines a publisher page shows are a string no registry entry answers for.**
The registry covers the four houses carrying most of the corpus, at 44 lines. Everywhere else a
publisher page lists the catalogued spelling as though it were a line, which is the honest fallback
and reads oddly where the string is the company's own name: 一迅社's page carries a line called
一迅社 with one book on it. `imprint strings that reach no line` is the count and it falls as houses
are curated.

**A credit page cannot yet say which of two people with one reading is which.** Seven pairs are
held apart under `homophones` and each page links the other, which is what the ruling asks for.
須藤佑実 against 須藤祐美 is still the one a source check should settle: both are girls×garden
comics books from ジーオーティー in the Avalon anthology line, which is one artist mis-keyed at one
source rather than two artists.

**`credit fields an identifier does not cover` is unchanged at 19** and the two credits separated
by nothing but a space are still in it. `狗之餌 廃狼` and `織日ちひろ 虫原` reach the corpus only
from release rows, a space is deliberately not a separator, and neither mints an identifier.

**196 author readings and 31 title readings cite a page a reader cannot open.** They point at
`api.openbd.jp/v1/get?isbn=`, which states the reading in its JSON and is not a document. Treated
like the 36 National Diet Library `/api` citations, withheld and counted, which took `citations
withheld from readers` from 36 to 244. openBD publishes no per-book reader page, so this falls only
when a reading is re-sourced somewhere a person can read it.

**577 reading conflicts are left and every one of them is a real disagreement.** The store held
1,142 and 565 were one reading written with a different word division, which `store.same_reading`
exists to prevent being called a conflict and which `_merge_group` was asking `==` about in the one
branch that fires when a claim is outranked. Fixed and swept. Of the 447 author conflicts left, 87
come from MangaUpdates, which is the source behind both alias bugs of 2026-08-08, so that subset
wants suspicion before it wants a display. Nothing renders the list.

**The role is on 601 of 4,351 edges, up from 14.** The works list keeps the job beside each name
now, out of the same traversal that rebuilds the field, and the print rows keep what MADB's bracket
said. What is left is the corpus rather than the pipeline: most platforms state a byline and no job.

### A date the shop states in its own blurb is a printing (2026-08-08)

**The owner's ruling.** A date コミックシーモア states inside its own description of a work attests
that date. The previous round found these and left them, because nothing said whether a shop
writing a date in prose is the shop stating a fact. It is, and what it states is a PRINTING, so it
outranks the delivery date on the same row under the rule that a print date always wins.

**What the cache holds.** 277 of the 1,833 captured work pages mention a doujin word in the shop's
blurb, and 58 of those put a date or a numbered sales event beside it. 33 yielded a date: 24 at
month precision, six at year precision and three at day precision. All 33 were dated by delivery
before this round and are now dated by a publication, so `shop-delivery-date` falls from 1,209 to
1,176. Of the 33, ten were `earlier-edition-unsourced`, which is the only follow-up state that was
ever work anybody could do, so that population falls from 165 to 155. The other 23 were already
settled under DEFINITIONS §6 and gain a better date without changing what is owed on them.

A promoted row leaves the follow-up measure altogether, which is stronger than being settled in it:
the measure exists to sort rows carrying the weakest date the database holds, and these no longer
carry it.

**Every one of the 33 precedes its own delivery date**, by gaps running from six weeks to thirteen
years, 森島明子's 2010 printing against a 2023 delivery being the longest. `a stated printing
precedes the delivery` is the invariant on that, and §14b is why it is worth having: `blurbdate`
reads a sentence in the description box and never opens a volume row, so 配信開始日 is a number it
cannot consult. A four-digit run picked out of a plot summary lands anywhere, and landing after the
shop began selling the file is the half of "anywhere" a machine can recognise.

**The blurb is read from a narrower span than the edition statement**, and the reason is worth
recording because it is the trap this round could most easily have fallen into. `description` reads
the whole `title_intro_box`, which carries the shop's own metadata table under the prose, and one of
its lines is `配信開始日 ： 2015年8月18日`. A date rule reading that span finds the line on all 1,971
cached pages and hands the delivery date back as though the shop had stated a printing.
`cmoa_volumes.synopsis` stops at the table. Reading the narrower span changes none of
`edition_statement`'s 174 and 79 answers and does move the loose doujin-word count from 284 to 277,
because seven pages carry the word in the shop's own tags rather than in its prose.

**An event number is recorded and is not turned into a date.** 36 rows name a sales event and 21 of
them name only that. The mapping exists and this corpus even states four points on it, but three
things argued against assembling one. Comiket 98 was cancelled in 2020 and its number was consumed
anyway, so counting two events to the year across that gap returns a wrong year in silence.
`関西コミティア68` is a different series from `COMITIA68` and a table keyed on the number alone merges
them, which is why `blurbdate.sold_at` matches the regional name first and why the test pins it.
And a table nobody sourced is a second producer of a fact, which is the shape STANDING-INSTRUCTIONS
§3 attributes seven shipped bugs to. So the row keeps its delivery date, records `comitia 150` or
`comiket 102`, and stays open. Nine of the rows still in `earlier-edition-unsourced` name an event,
which makes them the most answerable rows in that population: an event calendar dates them.

**The counter-cases, which are most of the work.** A blurb is full of numbers. Page counts run to
【165ページ】, `創作百合同人誌15冊発刊記念` puts a count of books next to a publishing word,
`1000年後の地球` and `結婚でこの地を離れて12年` are plot, `2025年5月現在` says what is true today,
`2011年～2014年にかけて` is a range that dates no single edition, and `個人誌『夢落 2021年3月号』` is an
issue label inside a title. A date is taken only where a publishing word sits within twenty
characters of it, and 発売 is deliberately not one of those words: a shop uses it to announce a
different book's release. `adapters/test_blurbdate.py` pins all of these.

The three refusals the previous round pinned are inherited rather than restated. `blurbdate.dates`
asks `delivery.edition_statement` first, so a page that never said what edition it is can hold
whatever dates it likes and none of them is about a printing of it. 同人誌風マンガ, コミティアの人気作家
and 参加した同人誌即売会で each stay refused with a date bolted on.

**One page the sweep can see and the rules cannot.** cmoa title 247855 reads
`※著者個人誌『夢落 2021年3月号』に描き下し原稿を追加した合冊版です`, which says plainly that the file is
a 合冊版 of the author's own 個人誌, and `delivery.edition_statement` answers None on it because none of
its patterns covers 合冊版 predicated on 個人誌. Widening them would move the 174 and 79 counts that this
round and the last one both report, so it is left as a gap to close deliberately rather than in
passing.

### An anchor must not match inside the word before it (2026-08-08)

**What was wrong.** `kana.align` places a reading over a surface by treating kana and punctuation as
anchors and searching for a split that spells the reading. The search backtracks, so it is complete,
but the first solution it finds is arbitrary: a kanji run is tried shortest first and nothing says a
kanji run should read as few kana as possible. `私の女神が今日も推せる` against
`ワタシ ノ メガミ ガ キョウ モ オセル` came back with 女神 under メ and 今日 under ミガキョウ, because
the anchor が matched the ガ INSIDE メガミ. `アイドル総選挙4位…魔王を倒す` did the same, を taking the
オ inside マオウ. Both spell their reading, so the producer's own gate passed them, and
`implausible ruby spans` caught them, which is why the gate went red and the readings went unstored.

**Why the readings went unstored is the part worth naming.** The reading of both titles is ordinary
Japanese with no name and no coinage in it, and neither was ever in doubt. What could not be derived
was the ruby. Storing a reading drops pass 4's spans by design, `build.py` re-derives them, and the
derivation was broken, so a correct reading could not be committed and the works kept an
`unverified` mark that says the reading may be wrong. The mark was reporting the fact that was fine.

**The fix, and the constraint on any fix.** Putting the arithmetic `implausible ruby spans` does
into the solver would make the check true by construction for spans the solver produced, which is
§14b's second shape. So the solver was given something else to work from: the analyser's own word
boundaries in the reading, which were being thrown away. An anchor that STARTS inside one of those
words has to reach at least the end of that word. That is what okurigana is, kana trailing the stem
of ONE word, so 推 under オ followed by せる taking セル is admitted and が stopping in the middle of
メガミ is not.

**The check keeps its independence because the two read different things.** `implausible ruby spans`
counts kana against kanji on the rendered result and never looks at the segmentation; the solver
reads the segmentation and never counts a kanji. `毎月庭つき大家つき` against
`マイツキ ニワツキ オオヤツキ` is the case that proves they are not the same measure: 毎月庭 under マイ
honours every word boundary, because ツキ does end マイツキ, and it still puts three kanji under two
kana. The solver cannot see that and the check can.

**Measured before it was believed.** Every surface and reading the store holds was aligned both
ways. Three of 1,434 curated and sourced pairs change, all of them improvements, and the store's
implausible-span count falls from 10 to 8. Nothing that aligned before fails to align now, and
nothing that was refused before is placed now: `能面 battle girl納言` is the case that made the rule,
where pinning does find a placement and the placement puts `girl` over `girl`, so the pinned result
is only ever accepted where the unpinned search also found one.

**The remaining class, which this does not touch.** The 24 implausible spans left across the whole
name store fall into one shape: the SURFACE carries a space and the reading does not divide the same
way. `幕末女子高生 鬼と夜明け` reads `バクマツ ジョシコウセイ   オニ ト ヨアケ`, four reading words
against two surface parts, and the equal-count fast path cannot use the boundary that is written on
both sides. Six author names are the same shape with no spaces in the reading at all, `三田 織` against
`ミタオリ`. A surface space is a harder boundary than anything the solver currently trusts, and using
it is the next piece of this.

**A curated `furigana_spans` was considered and refused.** `curate.py` could admit the field, and a
reviewer could then record correct ruby beside a reading the aligner cannot derive. It was refused.
The defect was a class and not two rows, so curation would have left three other titles wrong and
would have reached none of them. A hand-recorded span set is a second producer of a fact the reading
already determines, which STANDING-INSTRUCTIONS §3 warns about, and it lets a reviewer record spans
that agree with no reading at all. Papering over an aligner fault one row at a time also lowers the
count that would otherwise find the class, so the measure stops being able to see what it was built
to see.

The case for it is not empty and is worth keeping in view. A title whose correct ruby no reading can
produce, which is what the remaining class above is, has nowhere to be recorded today. Admit the
field when that is the problem being solved, and not as a way around a solver bug.
## 27. The line the extractor could not spell (2026-08-08)

`adapters/madb/extract.IMPRINTS` held four spellings of 一迅社's 百合姫 line and the abbreviated
logotype was not among them. 一迅社 prints `YH comics` on the spine beside the spelt-out form every
year from 2015, on volumes of the same series, so release 1.2.18 states it on 94 volume records and
38 series records. Every one of the 132 names 一迅社 as the publisher, which is what made the
substring safe to add: the pattern was matched against the normalised brand of all 401,311 book and
139,130 series records before it was written, and it reaches this house and no other.

**What the fault cost, measured on the two sides it fell on.** The corpus went from 302 works and
646 volumes on this route to **351 works and 740 volumes**. 43 of the 49 new works were already
here, admitted on a retailer's shelf and stored `marketing_label: none`, so what they gained is the
publisher-side label their own books carry. Six are works this database did not hold at all:
これでわかってよ!, イヴとイヴ, 私に体、売ってみない?, レズ風俗アンソロジーリピーター,
いちゃらぶしかない百合アンソロジーコミックsugar and 小春と湊 : わたしのパートナーは女の子. The
remaining volumes landed on works already held, which is the quieter half: 星屑テレパス went from 6
volumes to 10 and one 21-volume run to 23.

**A budget rose because the fault stopped being invisible.** `labels with nothing to quote` reads 0
where it now reads 49, and the change is in what is measured rather than in what is wrong. That
budget counts records carrying a yuri label whose imprint states no term saying so, and its subject
is `YURI_TERM_IN_IMPRINT`, which recognises 百合, ガールズラブ and yuri. `YH` is none of those. The
works that would have been counted never had the label that would have put them in the count, so a
zero read as nothing to fix while 49 records were in exactly the state it exists to find.

**Teaching the pattern `YH` was considered and is wrong.** It would empty the class by fiat: the
check asks whether the imprint a work page quotes says anything a reader can weigh, and `YH comics`
does not say it to a reader, whatever it says to a cataloguer. A measure that recognises the
abbreviation stops being able to report the case it was written for.

**What DID reduce it, from 51 to 49.** Adding the spelling made the series brand of C434622 and
C353604 match where it had not, and both records went from quoting `Yurihime comics` and
`Yuri-hime comics anthology series` to quoting an abbreviation that states nothing. That is the
same fault as the umbrella `IDコミックス` one spelling further in: the label is right and the
evidence beside it has stopped saying anything. `extract.imprint_of` now ranks a mute spelling last
among the source's own, so it is taken only where the whole chain offers nothing else. The other 49
offer nothing else, and their records say so honestly.

**What the six new works brought with them.** Two credits sharing a reading, from one MADB creator
field holding two names followed by their two readings, `ひあるろん / 達磨 / ダルマ / ヒアルロン`;
both are ruled and merged in `data/identity/credit-rulings.yaml`. One duplicate row: 一迅社's 2018
printing of 私に体、売ってみない? against BOOK☆WALKER's 私に体、売ってみない？【単行本版】 under
コンパス, which `data/source/madb-title/` had already dated from the same ISBN, so the two are
merged on the ISBN and not on the title. And rises of two, one and six in
`kana names with no stated division`, `author readings no source states` and
`works showing a romanisation`, which are six works arriving with no reading anybody has collected.

**The lesson is about health floors and not about the spelling.** `MIN_VOLUMES` is 400 and the pass
was matching 646, so nothing in the adapter could have said that a quarter of the line was missing.
A floor catches a selection that has stopped working and cannot catch one that never covered its
subject. What found this was reading the release's own brand field and counting the spellings, which
is what `docs/MADB.md` records and what no assertion in the pipeline does.

## 28. The eleven line names, and the two lookups that hid them (2026-08-08)

The imprint registry chose a canonical name for each of its 44 lines after the publisher naming
rounds had run, so eleven names reached a reader in Japanese having never been offered for naming.
All eleven render now. Two of them needed a source; six needed nothing but a lookup that folds the
way the interface does; and the remaining three were already answered and could not be found.

### What each of the eleven rests on

**ハルタコミックス → HARTA COMIX**, and the letters are the publisher's. Every one of the 11 rows
this corpus holds is catalogued HARTA COMIX, the National Diet Library files the series title of
ISBN 9784047380905 the same way, and KADOKAWA addresses the ハルタ label on its own platform at
`comic-walker.com/label/harta`. The label index prints the Japanese and no Latin form as text, so
the address is what makes this the company's spelling rather than ours. `official-jp`.

**MANGAバル コミックス → MANGA Bar Comics.** KADOKAWA's own English site names the magazine MANGA
Bar and links it to `comic-walker.com/label/bar`, at
`group.kadokawa.co.jp/global/business/publishing.html`. That settles バル, which is the only element
that was in question: MANGA is Latin on the label and コミックス is the English word it stands for.
`official-jp`.

**HOWLコミックス → HOWL Comics.** The same reading IDコミックス already gets in this file: HOWL is
一迅社's own letters and not a transcription of anything. The National Diet Library files the series
title of ISBN 9784758026055 as Howl comics and both rows of this corpus are catalogued that way.
一迅社 publishes no label index, which is why the Japanese name still comes from BOOK☆WALKER's list
for the house. `official-jp`.

**4コマKINGSぱれっとコミックス → 4-koma KINGS Palette Comics**, a romanisation and the only one of
the eleven. 4コマ names the four-panel form and ぱれっと is the magazine's own kana spelling of
palette, so both are ours. `publisher readings nobody has settled` does not move, because the
catalogued spelling `4コマkingsぱれっとcomics` was already in it and this is the second key on one
decision.

**The other seven were already named** and the map could not be asked for them. FUZコミックス,
まんがタイムKRコミックスつぼみシリーズ, MFC キューンシリーズ, MFC ジーンピクシブシリーズ and the
アライブ, ジーン and フラッパー strands of MFコミックス all had a reviewed English name and a
sourced reading, written for the string the corpus carries.

### The lookup, which is the finding

The store is keyed by the catalogued string and the registry names each line NFKC-normalised with
ordinary spaces. Those differ by nothing a reader could see: `ＦＵＺコミックス` against
`FUZコミックス`, `MFC　キューンシリーズ` with an ideographic space against `MFC キューンシリーズ`
with a plain one. An exact lookup answered for the catalogued form and not for the line's own name,
so `publishers.english` asks the folded key last, after the exact ones, using the interface's own
`fold` and not the registry's. Measured before it was written: exactly two keys in the store collide
under that fold and both pairs already agree on their English, so nothing here decides between two
records.

**And a second lookup, in `build.py`, which is why MFC キューンシリーズ was not even on the list.**
The pass that renders a line name skips a name the map already holds, and it tested the
space-stripped fold. `MFCキューンシリーズ` was in the map under the catalogued spelling, so the pass
concluded the line was named. `pubRec` in `app.js` tries the string and its NFKC form and does not
remove spaces, so it asked for `MFC キューンシリーズ` and got nothing, and 35 rows showed the line in
Japanese. The skip now asks what the reader's lookup asks. This is §14b in its plainest form: a
producer's test for "do I have this already" has to be the consumer's lookup, or it answers a
question nobody is asking.

**`publisher keys the interface misses` was measuring the previous interface.** It reads 5 where it
now reads 1, and the fall is a repair to the measure rather than to the data. `check.py` holds a
transcription of `imprintOf` on purpose, as a copy of the CONSUMER, and when `imprintOf` stopped
segmenting and started returning the registry's canonical name the transcription followed it while
the caller went on invoking it with no map. So the copy resolved every imprint string to itself,
which is what the old interface did: it counted four catalogued strings that had stopped being shown
and could not see eleven canonical names that were. A copy of the consumer has to be CALLED the way
the consumer is called.

### What is left, and it is not a name

`ガンガンコミックスonline　／　GC ONLIN` is the one string still reaching a reader in Japanese. It is
a truncated catalogued value with a separator in it, not a label anybody prints, and §29 places it.

## 29. Working the imprint field outward from the corpus (2026-08-08)

The registry covered four houses when this round started and `imprint strings that reach no line`
stood at 278. It covers 33 houses now and the budget reads **140**. 114 lines were added over 132
strings, so the ratio is nearer one to one than the first four houses gave, and the reason is in the
data rather than in the curating: 一迅社 writes its yuri line about twenty ways and most houses write
each of theirs once.

### What the residue is, and it is mostly one shape

141 strings on 451 rows. **99 of them, on 359 rows, are the imprint field repeating the publisher**,
which is what a shop's individual-publishing service produces: the artist is the publisher of record
and the cataloguer has nothing else to put in the field. Those are not lines and this file refuses
them, which `test_imprints.py` pins on ガレットワークス, a company whose books クロスフォリオ出版
delivers and which carries 37 of the 92 remaining rows on its own.

The other 42 strings, on 92 rows, are ordinary lines nobody has curated: 6 rows at ブシロードワークス,
6 at 小学館 and 6 at 少年画報社, and a long tail of one and two. What each of them needs is somebody
reading the house.

### Two shapes the file refuses, and both are rulings rather than gaps

**A company name in the imprint field.** A distributor writing who made the book, not a line.

**A magazine name where nothing says it stands for the book line.** 百合姫 could be folded because
MADB's own `IDコミックス. Yurihime comics = コミック百合姫` writes the equation out. コミックハイ!,
楽園, ヤングキング, まんがタイムきらら and 講談社's and 小学館's own magazine names have no such
statement, so folding them would decide by resemblance what only a source can decide. Both refusals
are asserted per house in `test_imprints.py`, so a later round that folds one in shows up as a number
falling rather than as a tidy-up.

### The curating unit is a house

Curating by string places whatever somebody happened to look at and leaves a count nobody can read.
Curating a house means reading what it publishes, deciding every string it carries, and recording
the ones the file refuses, which is what makes the per-house residue an assertion. 15 houses now sit
at zero.

### Where a name came from, house by house

Most of these houses index their books by magazine and by title and publish no list of book lines,
so `name_basis: corpus` carries most of the entries and each says what was read. Where a publisher
page did answer, it is cited: 新書館's comics site names Wings in Latin in its own navigation,
小学館's e-comic store addresses デジコレ at `e-comi.shogakukan.co.jp/digicolle`, forcs addresses
じるみて at `forcs-comic.jp/jilmitte`, and KADOKAWA's label index carries コミックエッセイ.

### The truncated string, which was never a naming question

`ガンガンコミックスonline　／　GC ONLIN` is a catalogued value cut off mid-word with the cataloguer's
separator still in it. The segment before the separator is `ガンガンコミックスonline`, which is the
line, so the row reaches it and the truncation is never read as anything. `GC ONLIN` is not listed as
a spelling: it is the same name abbreviated and then cut, and giving it an entry would put a
catalogue artefact in front of a reader. That was the last string in
`publisher keys the interface misses`, which now reads 0.

### One string the segmenter will not split, listed whole instead

`Action comics : comic high's brand` uses ISBD's " : ", which `publishers.segments` does not know, so
the string is never taken apart. The module docstring names it as the case that shows up in the
unresolved count rather than being split silently. It is listed as a spelling of comic high's brand
in full, which places the row without teaching the segmenter a separator on the strength of one
example.

## 30. What is still Japanese on an English credit line, and why each class is stuck (2026-08-08)

`renderings still Japanese in English mode` fell from 334 to 113 when the credit division moved into
the build. The whole of the remainder is a NAME, which is the state NAMES-PLAN §6 calls finished, and
it divides into four classes with different prospects. Measured over 172 surviving runs of kana or
kanji across 113 renderings.

**94 runs: a credit with no record in the name store.** `さばみぞれ`, `二月公`, `巻本梅実`,
`なおたけ`, `黒布直導`, `我美蘭`. No source this project reads states a reading, and §6 says show the
Japanese rather than guess one. This falls when a research pass finds a source, and nothing an
interface change can do will move it.

**25 runs: an editorial desk.** `Be編集部`, `百合姫編集部`, `ちゃお編集部`, `アンブル編集部`,
`comicGAGA編集部`, `まんがタイムきららＭＡＸ編集部`. A magazine's name with 編集部 after it, credited
as the compiler of an anthology. These are closable and are not closed: 編集部 is a common noun and
glossing it is translation rather than a guess at a reading, so `Be編集部` could read "Be editorial
department" today. It was left alone because the gloss would have to fire on a NAME field, which
means a second producer of a name rendering beside the store, and STANDING-INSTRUCTIONS §3 counts
seven shipped bugs from that shape. The right home is a record in the store with `kind: venue`,
which is where the credit registry already files these.

**15 runs: a record the store holds with no reading.** `角川青羽`, `伊実`, `時一二`. The store has
met the credit and every source it asked came back empty. Same prospect as the first class and a
shorter distance to travel, since the record exists and only wants a source.

**A handful inside a compound the store knows in part.** `さりい・Ｂ` and `るいす・まくられん` are one
credit each, and the store can render one half. Splitting them would print half of somebody's name,
which `adapters/names/inputs.py` records as the reason ・ is not a separator for a caller that
prints. Nothing here is a gap; it is the rule working.

**What moved out of this count entirely.** A role with no gloss, `ほか`, a doubled bracket, a
reading printed beside its own name, and a Latin pen name a cataloguer typed in full width. Each of
those has a right answer, and each is now an invariant that blocks rather than a number that
tolerates.

## 31. The work page's byline was measured by nothing (2026-08-09)

A reader was shown `???? · Bun?Bun` on w01700 for the credit `安田剛助・文尾文`, two artists whose
readings openBD and the publisher both state. Every gate was green and a probe over the interface
table reported zero.

**What the fault was.** `creditLine` shortens a byline naming more people than a line holds. It
shortened by cutting the FIELD on the slash and handing the first four pieces to `linkedCredits` as
a field of their own. That string is not a field the build ever divided, so `credit_parts` answered
nothing for it and the whole line fell to the floor, which spells a run it cannot look up one
character at a time. `安田剛助・文尾文` is in no map on purpose: the corpus settled it as two people,
so the build floored the two of them apart. 79 rows were shortened that way and 46 more were counted
wrong, because a field writes two people with a comma or a ・ as readily as with a slash.

**Why nothing saw it.** `adapters/interface.py` ruled `series[].author` through `authorLabel` and
through `linkedCredits`, and the work page calls neither directly: it calls `creditLine`, which
calls `linkedCredits` for what is left after the cut. Every check was measuring the callee. That is
STANDING-INSTRUCTIONS §14b in the form the section does not spell out: not a check sharing its
subject's assumption, but a check pointed at the function next to the one a reader meets.

`creditLine` is a surface now, and `no name is spelled with question marks` is the invariant. It
counts question marks in the answer against question marks in the question, so it consults no store
and no division; it holds on names, houses and roles, and titles are excluded because a translation
may honestly gain one. Its canary is the two statements the file held, restored.

### Two budgets moved for this, in opposite directions

`renderings resting on a mechanical romanisation` rose 626 to 798, and neither half of that is
anything getting worse.

163 of it is the work page byline being counted at all. 3,037 renderings joined the population when
`creditLine` became a surface, and the marks on them were already on the page.

9 of it is the mark landing where it belongs. A byline that fell to the floor whole carried ONE mark
for the whole line, and the line now renders each person from the store and marks the ones that rest
on our own romanisation. Two honest marks in place of one wrong one is a rise, and the rule against
suppressing a mark to make a number fall says to take it.

`interface reads outside an entry point` fell 13 to 12. `creditLine` had an exception in
`entrypoints.SAFE` for reading the byline in order to split it on the slash. It is a ruled entry
point now, so the read is inside a renderer and the exception went with the split.

### One person, two romanisations, decided by a role bracket

`[著]安田剛助` shipped as `[ Cho ] Yasuda Takesuke` while 安田剛助 alone shipped as `Yasuda Kōsuke`.
`build._recompose_credit` rebuilds a credit line out of the people in it and declined to rebuild a
line naming one person plus a role, because the splitter peels the `[著]` off and composing from the
parts alone would have published the name with the job gone. Declining kept the job and froze the
name: a phrase is written once by the analyser and never revisited, so openBD's ヤスダ コウスケ could
not reach it. 207 credit fields were in that state.

The role is put back now, spelled from the floor, which is the build's one romaniser and the map the
interface already falls back to. It reads `[Cho]Yasuda Kōsuke`, and it will read `[author]Yasuda
Kōsuke` wherever `credit_parts` reaches the page, because glossing a role is `roleWord`'s job in
kari/app.js and a second table here would be a second producer of it.

`a person is spelled one way` could not see this: it compares a phrase with the store record under
the same key, and `[著]安田剛助` is not a key the store holds, so there was nothing to compare.
`credit phrases spelling a person otherwise` asks the shipped division who the field names and looks
those people up. It reads 207 on the store as this branch found it and falls to 70 on the next
build. The 70 are the all-or-nothing rule working: a line is left as the analyser wrote it where any
one person on it has no rendering yet.

**It is not one of `names rendered two ways`.** That budget reads 3 and counts a different class
entirely: strings the shipped maps spell one way as a publisher and another way as a person, which
is what a self-published work produces. The three are `すたひろ`, filed Sutahiro as a publisher and
Stu-Hiro as a person; `ガレットワークス`, Galette Works against Garettowākusu; and `ネジ式13番地`,
Nejishiki 13-banchi against Nejishikijūsanbanchi. None of them moves for this work.

## 32. The inclusion test had never run (2026-08-09)

DEFINITIONS §6 says a work is in scope if its first publication venue was in Japan, that author
nationality is irrelevant, and that `first_publication` IS the inclusion test. The field carrying
the answer was the literal `"JP"`, written in `build.py` twice and in `adapters/cmoa_volumes.py`
once. So 2,564 works asserted Japan, none of them had been asked, and the invariant over the field
asked whether it was non-empty, which a constant satisfies for ever.

**Why no source can answer it.** Works enter through MADB, openBD, コミックシーモア and
BOOK☆WALKER, and every one of those catalogues the JAPANESE EDITION. A Japanese edition of a comic
first published in the United States and a Japanese edition of a comic first published in Tokyo are
the same shape of record, so the country read off the edition is `JP` for both. The value was
derived from the one thing that cannot tell the two cases apart, which is STANDING-INSTRUCTIONS
§14b in its purest form.

`adapters/facts/origin` decides the field now. It reads two signals, a credited translator and a
publisher's line flagged in `data/names/imprints.yaml` as one that brings comics published abroad
to Japan, and it treats both as evidence rather than proof: a 現代語訳 of a Japanese classic is
translated and Japanese, and nothing stops a house putting a Japanese work on any line it runs.
Neither signal retracts anything. Each asks for a person to read the publisher's page for that
work, and the answer goes in `data/scope.yaml` with the page cited.

**What the corpus-wide run found.** Nothing attests a first publication country for any work in the
database. The count is the budget `works whose first publication country is unattested`, at 2,562
of 2,562 the day it was written, and it can only come down one work at a time: what closes a row is
a serialisation venue named on a publisher's page, and no bulk catalogue carries one. The two works
that entered on a foreign line are out, both on the publisher's own words.

**Two out of scope, refused.** `サンストーン` is Stjepan Šejić's Sunstone, and 誠文堂新光社's own
page gives レーベル名 G-NOVELS, credits 上田香子 as 翻訳者名 and calls the edition a 邦訳化; MADB
says the same thing in its own notation, crediting 訳. `オルターエゴ` is Ana C. Sánchez's Spanish
original, and KADOKAWA's own product page calls it スペイン発. Both are held out of everything the
site serves, by the register a content flag goes into, so all six surfaces are covered by a
mechanism that has already been made to work.

**A line flag would not have caught the second one, and that is the finding.** KADOKAWA files
オルターエゴ under MFC, the same general line that carries its ordinary Japanese titles, and our
record holds exactly that pair. No flag on any imprint reaches it and none ever would. The reachable
route was the product page, one work at a time, which is why the fact produces candidates and a
person produces rulings.

**Two more are open.** `落差` and `ON a LEASH ~ 戦場で出会った彼女に囚われて ~` are on BOOK☆WALKER
under 出版社 SNP, レーベル NETCOMICS, sold by the chapter, credited to romanised Korean names, one of
them summarised by the shop as running between Seoul and Busan. That is what a licensed webtoon looks
like and §6 excludes one outright. Nothing publisher-side has been found for SNP or for the label,
and a shop's label field is not the publisher saying anything, so both are recorded `review` in
`data/scope.yaml` and stay in the corpus. The budget `scope questions left open` counts them.

**What is being asked of the project owner.** §6 requires the country because it answers the scope
question, and the honest measurement is that it is unanswered for the whole corpus. The database
therefore holds 2,562 works whose inclusion test has not run, which was equally true yesterday and
is now visible. Whether that stands, and for how long, is the owner's call and not a gate's: the
alternative is refusing every work no publisher page has been read for, which would empty the
catalogue to spare us a number.

## ガンガンONLINE was targeted by nothing. Found and closed 2026-08-10

`adapters/ganganonline/releases.py` selects its works out of `data/coverage/render-targets.yaml` by
id. The section was in that file until commit `544a462` dropped it, and from then on every run of
the adapter exited `no ganganonline section in data/coverage/render-targets.yaml` before reading a
page. It was listed `optional` in `adapters/stage-a.yaml`, so each run recorded the failure and
carried on.

**Why it stayed hidden is the part worth keeping.** The failure line was real and it was permanent,
so it stopped carrying information: the 2026-08-10 run reported `failed (2): ganganonline,
kadokomi`, and `kadokomi` was a genuine new break that had been dying the same way. One unfixable
failure beside it is what made the pair readable as normal.

**It was also the same fault as three entries in Stage C's unreached list.** 藤髪の魔女, 温室のアトリエ
and 私がモテないのはどう考えてもお前らが悪い! were reported `no route yielded a dated chapter list`, and
all three are ガンガンONLINE works. The adapter's own docstring says why the rendered route cannot
read this platform: the visible chapter strip shows 次回更新 for the newest entry, and the dates,
author and access all sit in `<script id="__NEXT_DATA__">` instead. The adapter written for that was
never given anything to read.

The section is restored from `97f7d30` with its 13 works and the stage entry is back. Verified by
running it: 4 works resolved, 8 chapters, 4 free and 4 purchase, every one with an author, which
matches the 2026-08-02 capture. The other 9 state no dated chapter or no page state, which is what a
completed series on this platform looks like. `check.inv_the_pipeline_runs_from_a_clean_checkout`
now fails if a stage entry names a section its targets file does not hold.

## What the 2026-08-10 update run reported, work by work

The run named 21 unreached works, 4 nicovideo failures, 2 degraded platforms and 4 platforms
parsing nothing. Most of it is a fact about a platform. What follows is the residue, so that a later
reader does not re-derive the benign half.

**Platforms that print no per-chapter date at all.** 獄門撫子此処ニ在リ on てれびくん lists
`10話 9話 11話` and carries no date anywhere; the same work is reached on コロコロオンライン with 10
dated chapters. 私の魂を食べて下さい! on COMICリュウ and 横槍メンゴ新作読切シリーズ on ヤンジャン+ are the
same: across all three ynjn captures the entire DOM holds two dates, one of them the Unix epoch.
球詠 on comic-fuz draws only volume 発売日 on the web page, and its 228 chapters come from the
dedicated adapter. Selectors for dates that do not exist cannot be written, and these are recorded
so nobody tries.

The four nicovideo failures are ニコニコ's own error page, 9.7 KB against about 120 KB for a work
page: two say 閲覧できません and two say 非公開です. `data/fixtures/nicovideo/error-page.fixture` is cut
from one of them.

**ダ・ヴィンチニュース refused the runner and answers us here.** The adapter counts only transport
errors and all four fetches raised one on the GitHub runner; the same host returns 200 to the same
user agent from a developer machine, and `data/source/webpages/generic-ddnavi-com.yaml` holds those
four works from a local run. `ddnavi.com` is in `build.PROMO_HOSTS`, so nothing depends on it.

## A one-shot states one date and no chapter. Open, 2026-08-10

`ツイてるギャルとミエてる陰キャ` on きら星ポータル prints `2026年6月17日更新!` and `読み切り`. The
extractors need a chapter-shaped label before they will keep a date, and a 読み切り offers none, so a
date the platform states plainly is discarded. `data/coverage/unreached.yaml` records the reason as
"carries no dated chapter list", which is wrong: the page carries a date and no chapter.

This is a class rather than one work: every 読み切り on a platform that states a single work-level
date is in it. ニコニコ already has the shape this wants, a work-level date with the release typed as
a one-shot. Applying it here is a design decision about what a release IS when the work is one
chapter long, which is the project owner's to make, so it is recorded rather than patched.

## Addresses in the coverage files that no longer resolve. Open, 2026-08-10

Three works are listed as unreachable at addresses that have moved, while the corpus holds them in
full from another route:

| Work | The address that is recorded | What we hold |
|---|---|---|
| `ぬるめた` | `comic-fuz.com/series/2389`, a 404 | 75 chapters, from the dedicated adapter at `/manga/2389` |
| `ガールミートガール` | `sonorama.asahi.com`, gone | 26 dated chapters at `asacomi.jp/series/d67c4f256e18f` |
| `世界で一番おっぱいが好き！` | `www.mangabox.me/reader/262412/`, which redirects to the site front page | 75 chapters on カドコミ |

`adapters/dedicated.py` now keeps the per-work routes off hosts an adapter of ours reads, which
covers the first. The other two are stale strings in `data/coverage/remaining.yaml`, and rewriting
that file from what the dedicated adapters actually hold would shrink the unreached list honestly.
That was not done here because it needs all 70 entries checked and only these three were.

## Access is stated by the route and not by the platform. Found 2026-08-10

26 attested rows carry an episode title and an author and no access state. They are not a moved
selector, which is what the field audit in the update workflow was built to catch, and counting them
together with that fault had set the audit one row from firing on the wrong thing.

マガポケ is the case that explains it. It reaches us two ways, and `magapoke-feeds.yaml` carries
access on 0 of its 1,956 chapters while the rendered route carries it on nearly all of them, so a
work reached only by the feed arrives with none. 31 of its 48 rows have access and 17 do not.
チャンピオンクロス is 11 of 15. マイナビニュース states none at all on any of its 3.

The audit counts the two separately now. A row with no episode title or no author is a selector that
has moved and there are none of those, so that tripwire sits at 3 where it can still see the first
one. A row with no access is measured against the asymmetry above.

**What would close it** is reading マガポケ's access on the feed route, or preferring the rendered
route for a work both cover. Neither is done here: the first needs the feed to state something it
does not appear to, and the second is a change to how routes are ranked, which reaches further than
one platform.

## The discovery queue was dead, and it was one attribute. Fixed 2026-08-10

`adapters/webcomics/coverage.py` reads Web漫画アンテナ's 百合 tag, which REQUIREMENTS §1 names as a
first-class discovery mechanism. It had been returning 0 listings over 8 pages on every run.

**The cause is one added attribute.** `parse` split the page on the literal `<div class="entry">`,
with the bracket immediately after the class, and webcomics.jp now writes
`<div class="entry" data-comic-no="203870">`. Everything else is where it was: 50 entries a page,
with `entry-title`, `entry-site`, `entry-date` and the id all present. The split now matches the tag
instead of one spelling of it, and both forms are pinned in `test_coverage.py`.

**Two guesses of mine were wrong on the way**, and the second was worse than the first. I read the
refusal as the host blocking the runner, on a Cloudflare header seen in MY response, and removed the
pass from the workflow on that reasoning. What settled it was running the adapter's own `fetch` and
`parse` against the live page from this machine: HTTP 200, 86,354 characters, zero entry blocks.
The evidence for the runner theory had been a byte count from curl, which I never parsed. Removing
the step would have hidden a parser fix behind a manual pass nobody was going to run.

**Nobody noticed for six days** because the pass could not report it. Its health check refuses to
write when page 1 yields almost nothing, and it sat below an `if not rows: break`, so 1 to 9 entries
exited loudly and 0 entries left quietly with a success code. The committed coverage files kept the
good 2026-08-04 data throughout, which is the refusal-to-write working, and is why nothing
downstream visibly broke.

**What it had cost.** The two files this pass writes are the target list for five of Stage A's
adapters: `comicfuz` and `webpages` read `webcomics-gap.yaml`, and `kadokomi`, `nicovideo` and
`generic` read `webcomics-works.yaml`. Frozen, those five went on fetching the works already named
and could not learn of a new one. The first run after the fix moved `works_missing` from 376 to 355.

The step carries `--force` now. `fetch` returns a cached page whenever one exists, so a cache that
once held an unparseable page is read for ever, and this pass is cheap enough to re-read.

## A まんがタイムSquare title arrives reversed around its full stop. Found 2026-08-10

`updates naming a work we do not hold` turned up two feed rows whose work is
`スクエア）。（ニセアイホンアイ` and `スクエア）。（腹割るウチらの秘密ごと！`, both on まんがタイムSquare,
both with an ordinary episode number and a working episode address. The works themselves are
`ニセアイホンアイ` and `腹割るウチらの秘密ごと！`, and MADB holds the first of them under that name.

The shape says what happened: a title of the form `作品名（まんがタイムスクエア）` has been split at its
`。` and the halves put back the wrong way round, so the bracket that opened the platform name now
closes the string and the work's own name follows it. Two rows, and neither can be browsed, searched
or classified because no work matches the string.

Not chased here. It wants the まんがタイムSquare capture read beside the adapter that writes it, and
what is recorded is the shape, so the next reader starts from the fault rather than from the count.

## A shop credits an anthology to "アンソロジー". Substituted 2026-08-11, two things left

BOOK☆WALKER writes `アンソロジー` in the creator field on 9 records and GigaViewer on 47: a shop
puts something there for every book it sells and has nobody to put for an anthology, so it writes
the format of the book. The string went through the credit splitter like a byline. `is_a_person`
tests how a credit is BUILT, digits and punctuation, or a number followed by a sentence, and this
is a word spelled the way a pen name is spelled, so nothing refused it.

`facts/credit/nobody` refuses it now and the row says `複数の作家 / Various` in place of a byline,
which is what an English catalogue writes for a book of many hands. An empty Author line would say
nobody made the book, and these have many.

**The published identifier is still there.** c01868 was minted for the string and
`credit/c01868/` is a live page headed アンソロジー telling a reader in two languages that these are
"the works that name this person", listing nine anthologies with the role 著 on one of them.
Nothing links to it now, and it is reachable by address.

`credit-rulings.yaml` has a `withdraw` decision for exactly this, a string that was never a credit
holding a published identifier, and it could not express this case: `_withdraw` required `to` to
name a live credit to send readers to, and there is nobody here to name. The precedent it was
written for, `１冊目：叔母さんは神絵師`, had one, because the same field really did name a person
beside the chapter title. This one names nobody at all. Closing it meant deciding what a reader who
follows a withdrawn address lands on when there is no successor. A withdrawal may now name no `to`:
the anchor is detached, nothing resolves to the identifier again, and it stays retired and empty.

**Whether the contributors are recorded elsewhere has not been looked for.** The substitution says
this SOURCE names none of them, which is true and is not the same as saying nobody knows. MADB
catalogues an anthology's contributors on some records, openBD carries an ONIX contributor list,
and the publisher's own page for a 百合姫 anthology lists the line-up. Nine works, and the route is
the same one the byline work already uses. Worth doing before the substitution is taken as final:
`複数の作家` is honest about what we hold and would be a poor answer if the names are a fetch away.

## The byline fallback is only correct for fields the build divided. Found 2026-08-11

`composedCredit` builds an English byline from `credit_parts`, the division the build ships. Where a
field has no division record the interface falls back to walking the raw string in place, and that
walk takes the role text out and leaves its punctuation behind:

    玉置こさめ(作) / あおと響(絵)   ->  Tama Oko Same[?]() / Ao To Hibiki[?](art)
    [著]アンソロジー               ->  []Ansorojī[?]
    ぐう(作画)水無瀬(原作)riritto  ->  Gū[?](art)Minase[?](story)riritto(character design)

An empty bracket where a role elided, and names glued to the role in front of them.

**No reader can reach it today.** All 2,611 distinct credit fields the build ships were rendered and
none shows an empty bracket or a glued name, because every one of them has a division record. The
three strings above were written by hand to probe the fallback, and the first of them came out of
`phrases.yaml` rather than out of any row.

What would surface it is a field shape the divider does not cover arriving from a new source, which
is the ordinary way this corpus grows. The fix is for the fallback to drop the punctuation with the
role it elides, and to join on `joiner()` the way the composed path does. It is left here rather
than fixed blind at the end of the change that found it.

## A work page that throws has no check behind it. Found 2026-08-11

`renderWorkPage` read `r.stated_next.platform` one line under a `(r.stated_next || {})` that
tolerates the field being absent, behind a test of how many sources the work has, which is a
different question. Every work with more than one source and no stated next update threw there and
the page came back with its header, its footer and nothing between: **227 of 3,042 rows**, each one
reachable by clicking the row, by a shared address, or by a reload. Fixed, and all 3,034 work pages
were then rendered in the browser to confirm it.

**Nothing guards it.** Every interface check here renders a LABEL, and a label function is handed
its row and reads nothing else. A page painter looks the work up in `SERIES` instead, which
`adapters/interface.js` has no way to set, so the one surface that draws a whole page is the one
surface no check can ask anything of.

Handing the harness `SERIES` was tried and is not enough. With the collection supplied the painter
returns without throwing even on a row that throws in a browser, and a `throw` planted on the
offending line is never reached: under the stub DOM the function leaves early. So a check written
that way passes because the painter does nothing, which is worse than no check. It was written,
measured, found vacuous and removed rather than left green.

What would close it is a `document` faithful enough for the painter to run: `querySelector` that
answers, elements that hold what is written into them, and a container the result can be read out
of. That is a larger piece of work than the fix that found it, and it is the piece that would let
every whole-page surface be checked rather than only the labels.

## One person, two credit identities, where the mechanism cannot say so. Found 2026-08-11

野宮りおん holds `c00627` and `Rion Nomiya` holds `c01650`; 犬井あゆ holds `c00774` and `Ayu Inui`
holds `c01630`. Each pair is one person. Both creators publish an English edition of their own work
and the shop credits the romanised name on it, so both spellings are real credit surfaces a source
wrote, and each has a page of its own.

**The evidence is plain and computable.** `野宮りおん` reads ノミヤ リオン and romanises to
`Nomiya Rion`; the other surface is `Rion Nomiya`, the same two elements in Western order. `犬井あゆ`
gives `Inui Ayu` against `Ayu Inui`.

**`credit-rulings.yaml` cannot express it.** That file is keyed on a SHARED READING, which is what
pairs `相崎うたう` with `アイザキウタウ`, and a Latin surface carries no reading at all. So the pair
is never proposed, `relation` is never asked, and there is nowhere to write the decision. Nothing
here is a judgement waiting to be made; the shape the judgement would be written in does not exist.

What would close it is a second pairing rule beside the reading one: a credit whose surface equals
another credit's romanisation, in either name order. The rulings file would then carry the pair like
any other and the existing `merge` decision applies unchanged. Left rather than forced, because
giving the Latin surface a reading purely to make the current file accept it would record evidence
nobody has.

Found while merging 24 translated editions onto the works they translate, which is what put both
spellings of each creator on one work.

## A credit belongs to a work, and a translated edition has credits of its own. Found 2026-08-11

Merging 24 translated editions onto the works they translate left five translators crediting
nothing: `Ｏｔｔｅｒｇｅｉｓｔ`, `Ｕｍｉｕｅ`, `ＧｉａｎｔＣａｖｅＭｕｓｈｒｏｏｍ`, `Ｌｉｔｔｌｅ　Ｊｕｓｔｉｃｅｓ` and
`ＷｅｅｋｌｙＥｖｅｒｙｄａｙ`. Before the merge each held an edition's own row and was credited there;
after it the work keeps the original's byline, `あとき`, which is right, and the edition's second
name has nowhere to sit.

**The corpus credits a WORK and has no place for a credit that belongs to one edition of it.**
`credit_identity.credits_on` takes names from a row's `author` and reads `credits` for roles alone,
so a name carried anywhere else earns no edge and reaches no page. Writing the translator into the
byline was tried and reverted within the hour: `あとき / Ｍａｇｐｉｅ` on 地底をゆく says Ｍａｇｐｉｅ
made the Japanese work, and they did not.

The record states no role either. BOOK☆WALKER writes `あとき / Ｍａｇｐｉｅ` flat, so *translator* is
an inference from the `【English ver.】` mark on the title rather than something a source says.

What would close it is a credit edge that carries which edition it is from, so a person's page can
say they are on a work through its English edition. That is a schema change to `credit-works.yaml`
and to the page, and it is the same shape as the question of whether a licensed English edition is
the same work at all, which the 2026-08-11 merges answered yes to.

## The discovery queue reaches no reader. Noted 2026-08-11

`build.py` prints `queue: 81 unconfirmed candidates` and that is the only place the number appears.
77 of them are `shop-query-title-only.yaml`, a shop hit whose title agreed with a work we hold and
whose credit did not, kept because a shop and this database disagreeing about who drew a book is a
lead about one of them. Each row carries both credits so a person can settle it by looking. The
other 4 are 百合ナビ announcements awaiting confirmation against the publisher or the platform.

**status.html's outstanding list does not carry either.** It shows `content_tier` 302,
`english_names` 102, `shelf_rows` 2462, `english_licences` 87 and `data_debts` 48, all through
`status.outstanding`, which reads some queue files and not these two. So 77 questions each answerable
by one person looking sit where nobody reading the site would find them.

That is the shape STANDING-INSTRUCTIONS §13 is about, and the same one the CI conclusion has: a
register that exists and cannot be observed. The work is to add both queues to `outstanding` with
what settling one involves, which is a change to `adapters/status.py` and to nothing else.

## Only one magazine can be told from a book. Noted 2026-08-12

A work page headed `収録巻` over 117 issues of コミック百合姫 claims a volume numbering they have
never had. VOLUMES-PLAN §3 stopped that for the one record where the format is stated: BOOK☆WALKER
writes `[雑誌]` after each of that magazine's issue titles, `volumenumber.is_periodical` reads it,
and the heading now says 収録号. Nothing infers the format anywhere else.

**So ガレット is headed as volumes and is a magazine.** Its issues run `No.2` to `No.37` with
`創刊号` for the first, which is an ordinary run of numbers and looks exactly like a book's.
まんがタイムきららＭＡＸ and ちゃおデラックスホラー are headed as volumes and are magazines too;
they carry date-shaped designations, so a rule reading the format out of the designation would find
them, and it would still miss ガレット while marking anything else that happens to be named by a
date.

The gap is that no source in the corpus states what a product IS except this one shop on this one
record. MADB files コミック百合姫 as an imprint on books rather than as a magazine of its own, and
the shelf captures state a genre. Settling it needs a source that says `magazine`, and until there
is one the honest position is that an untagged periodical is unmarked, which is the shape
`categories are not advertised equally` describes: an absent tag is not evidence of absence.

## A pass that exists, works, and nothing calls it. Found 2026-08-13

Three passes were found in one day that were written, tested, correct, and absent from
`adapters/stage-a.yaml` and from `update.yml`. Each ran when somebody remembered and then stopped.

  `resolve.py`'s name passes. 96 works rendered in Japanese in English-only mode, 95 of them with a
  title the platform prints in Latin that `pass0_cache` has always had a rule for.

  `adapters/shopquery/capture.py` and `adapters/madb/by_shop_query.py`. 639 works had been asked by
  hand and 52 were left; running them wrote 110 works and 465 volumes.

  `adapters/openbd/enrich.py`. `volumes with an isbn and no date` is a ZERO budget and went to 1 the
  moment printed works arrived, because an ISBN is a key into registries that state a date and
  nobody had done the lookup. It supplied 1,936 dates.

All three are wired now, and a fourth is not: `adapters/cmoa_volumes.py` (below). What has no
guard is the CLASS. An adapter with a `main()` that no manifest names is a capability this project
believes it has, and the belief is invisible: nothing fails, no count moves, and the number that
would have shown it sits at whatever the last manual run left. `modules without a test` is 0 and
proves nothing here, because the fault is not a missing test.

The route is a check that reads every `main()` under `adapters/` and asks which manifest or
workflow names it, with a list of the ones deliberately run by hand: `curate.py` is a person's tool
and `identity --merge` is a decision. Anything else with no caller is a pass nobody runs.

## コミックシーモア is asked what it shelves, never what it stocks. Found 2026-08-13

WORKS-PLAN §6 fixed this for BOOK☆WALKER: `shopquery/capture.py` asks whether the shop sells a work
this database already admits, rather than reading the shop's 百合 shelf as a candidate list. The
same gap is open at コミックシーモア and the same fix does not transfer.

`adapters/cmoa_volumes.py` reads work pages for the 1,844 works on cmoa's 百合・GL shelf and for
nothing else, so a work cmoa stocks and files under another genre is invisible exactly as
見える子ちゃん was on BOOK☆WALKER. The project owner found one by eye: 日常やめたらしたいこと is
listed on cmoa with a date and an ISBN, is one of the leads `by_shop_query` reports as reaching no
bibliography record, and is not on cmoa's yuri shelf in our data. Of the 187 creator-agreement
leads, 33 are on that shelf, and the rest cannot be counted at all.

**The search route is closed.** `by_shop_query` records why: cmoa's robots.txt disallows
`/search/result/` under `User-agent: *`. BOOK☆WALKER's search is what §6 rides on and cmoa offers
no permitted equivalent, so reaching a cmoa work page needs its address from somewhere else. That
is what makes this a gap rather than a task: the obvious route is not available and the alternative
is unidentified.

## 618 ISBNs from cmoa and not one date. Found 2026-08-13

`cmoa_volumes.py` states its own case for reading the page: 出版年月 "costs nothing beyond the page
already being fetched and it is the only route that works without an ISBN". `data/queue/cmoa-volumes.yaml`
holds 1,833 works read on 2026-08-05, 618 volumes carrying an ISBN, and **zero carrying a date**.

Either those pages state no 出版年月 or nothing reads it. The second is likelier, since the shop's
page for 日常やめたらしたいこと shows a date, and a route the module argues for and does not deliver
is the shape STANDING-INSTRUCTIONS §13 is about. Checking it costs one cached page and a look at
the parser; it is listed here rather than fixed because it was found at the end of a long session
and deserves a fresh reading.

`cmoa_volumes.py` is also in no manifest, which is the class above.

## Leads that reach no bibliography record are counted and not listed. Found 2026-08-13

`by_shop_query.py` reports 74 leads where the shop and this database agree and MADB holds nothing,
split 34 printed against 40 digital-only on the shop's own 底本発行日. That split is the useful part:
a hit stating a print date is a book that exists and a bibliography that is behind, and a hit
stating none is a digital-only edition with no print run to catalogue.

The list is capped at twelve, `unanswered[:12]`, and written nowhere. So 62 of the 74 are counted
and unnamed, and the 34 printed ones in particular are leads about MADB's coverage that nobody can
act on. `data/queue/shop-query-title-only.yaml` already exists for the 78 title-only hits, so the
queue-file pattern is there to copy.

## Six works reach us only through a GigaViewer Atom feed. Noted 2026-08-13

WORKS-PLAN §3 took the works with no page from 53 to 6 by widening the ニコニコ episode-list
worklist. The six that remain are named only in `web_releases` records, which carry episode titles
and dates and no chapter list, so they produce feed rows and no work row.

`series_feeds.py` runs for ichicomi alone, because only platforms declaring `series_pages` do work
without `--candidates`. Reaching コミックゼノン and サンデーうぇぶり that way needs the platform
registry extended rather than a worklist widened, which is why it was left.

**SIX IS NOW TWENTY-FOUR, and the daily run has not refreshed a per-series feed since 2 August.**
Measured 2026-08-24: 50 feed rows name 24 works with no record, of which 21 are held nowhere under
any fold and 3 are joins onto a spelling the corpus already has. Seven of the 21 are also counted by
`announced works the corpus does not hold`, which is the same works arriving by the other door.
Measured again 2026-08-27: 53 rows, 27 works, the same 3 joins and 24 held nowhere. Three more works
in three days, and 15 of the 19 per-series feeds still carry `retrieved: 2026-08-02`, so the rate is
roughly one new unheld work a day and nothing is taking any of them off the pile.

The registry limitation above is not idle: `stage-a.yaml` passes `--platform ichicomi` and says in
its own comment that "the rest exit immediately and always have", so on 2026-08-18 sixteen of the
nineteen `*-series-feeds.yaml` files still carried `retrieved: 2026-08-02`. Those per-series feeds
are what carry ACCESS, and the platform-wide atom feed carries none, so every chapter published on
those platforms since 2 August arrives priced by nothing. コミックDAYS is 43 of 43 priced under
`bootstrap` and 3 of 23 under `observed`, one route throughout, which is that split exactly.

**WHAT THE ADMISSION POLICY DOES AND DOES NOT REACH.** A work served openly by a known platform is
promoted into the target list automatically, and that is working: the adapters reach these works and
publish their releases. What no pass does is turn an attested release into a WORK record, because a
work record comes from the bibliographic sources or from the web-works confirmation, and a web
serialisation with no volume reaches neither. `budget_announced_works_the_corpus_does_not_hold` names
three causes for a rise and this is a fourth: the promotion ran, the adapter reached the work, the
fold reconciles the title, and the work still has no record. Each one needs an inclusion ruling in
`data/queue/unheld-works.yaml`, which is the slow half and the half worth not repeating.

## Four translated editions name a base work the corpus does not hold. Noted 2026-08-13

`facts/edition` matches a translated edition to the work it translates through the reading the two
spellings share, and resolves 3 of the 7 that were unjoined. The other 4 name a Japanese title
absent from the corpus entirely: 冷たい体温, ふたりの日記帳, 人間してる？ and 風の少女達へ, all
あとき on アトキンソン, each printing its English on the product beside the Japanese.

A join needs two ends and this has one. Whether an English edition may be the only record of a work
is a scope question rather than a matching one; the likelier explanation is that BOOK☆WALKER sells
the originals and nothing captured them, which is four fetches to settle.

## An instalment is not a chapter, and one word does both jobs. Found 2026-08-13

What a platform lists is what it will sell separately: often a PART of a chapter, sometimes a
notice, a special, or a read-through that is no chapter at all. What a work has is chapters, in its
own numbering. The build calls both `chapters` and the site drew one as the other:
彼女が先輩にNTRれたので ran 24 instalments with 22 free against 11 chapters with 10 free, and the
badge read `11/11 free`.

That case was fixed by taking the denominator from what the platform states. The WORD was not, and
`series[].sources[].chapters` still names instalments. The relational store's `offer.instalments`
is named for what it counts, which makes the discrepancy visible at the one place a reader of the
schema meets it, and it does not resolve it: the build's field keeps its name because renaming it
changes what the site is served.

**THERE ARE THREE COUNTS AND THE CORPUS HOLDS ONE.** The project owner named the third on
2026-08-13, and it is the one most likely to be missed.

  INSTALMENTS, what a platform sells as separate items. This is what the corpus counts, everywhere.

  NUMBERED CHAPTERS, the work's own 第1話 to 第N話. Fewer than the instalments where a platform
  splits a chapter to sell it in parts.

  LOGICAL UNITS, everything the work actually contains. MORE than the numbered chapters, because a
  volume carries omake, extras, afterwords and bonus strips that the numbering does not reach.

So the numbered chapters are neither the largest nor the smallest of the three, and a reader asking
how long a work is gets an answer about a shop's catalogue. Nothing states either of the other two,
so this needs a source rather than a fix: the platforms count what they sell, and the count of what
a work contains is on the book.

The narrower version is worth doing first: rename the build's field to say what it holds, and leave
the harder question of a work's own length to whatever can source it.

**WHAT A READER IS SHOWN IS A SEPARATE QUESTION**, ruled out of scope by the project owner on
2026-08-13, and out of STORE-PLAN's scope too. This entry is about what the corpus holds and what
it calls it. Whether a work page states instalments, chapters, both, or neither is an interface
decision that can only be made once there is something true to state, and it should be settled
where interface decisions are settled rather than folded into a schema change.

## A platform can carry one work as several listings, and nothing says which continue. Found 2026-08-13

STORE-PLAN §4 keyed an offer on its address after `(work, platform)` refused 11 rows. That is right
about what a platform PRESENTS and silent about what the listings mean. 10 pairs exist:

    田所さん                  ニコニコ漫画    119 and 16
    不器用ビンボーダンス       ニコニコ漫画    100, 100 and 67
    転生王女と天才令嬢の魔法革命  カドコミ       144 and 4
    やがて君になる             ニコニコ漫画    46 and 3

**THE TITLES SETTLE ONE OF THEM.** ニコニコ's own pages read `田所さん` at comic/41133 and
`田所さん（２）` at comic/55102: one work, a first run and a second, listed apart. So the corpus
holds two offers where a reader would say one serialisation continued.

**THE HUNDRED-PART THEORY WAS TESTED AND DOES NOT HOLD.** 不器用ビンボーダンス reads 100, 100 and
67, which looks like a cap. Only 3 offers in the whole corpus state exactly 100, two of them that
work's, and 田所さん runs 119 on the same platform. Whatever splits that work into three, a listing
limit of 100 is not it, and its three pages are not in the capture cache so nothing here can say
what does. Recorded because the number was suggestive and the conclusion did not follow from it.

**THE MODEL IS RIGHT AND THE RULING IS THE OWNER'S, 2026-08-13:** mirroring the site's own
breakdown is fine, PROVIDED every listing is represented. So `offer` keyed on its address stands,
and joining three listings into one run is not wanted. Nothing needs merging.

**WHICH MOVES THE GAP FROM MERGING TO COMPLETENESS.** The fault to fear is a listing we do not
hold: a capture that finds comic/41035 and misses comic/70296 understates the work by 67
instalments, and every count downstream is quietly short. Nothing verifies that the listings held
for a work are all of them, because that needs the platform's own index of what it carries under
one title, and no capture asks for it.

**MIRRORING NEEDS THE LISTING'S OWN NAME, AND THE BUILD DROPS IT.** The project owner asked where
this leaves the work page. `田所さん` is one work, `w00185`: 4 volumes on ヴァルキリーコミックス,
and three web rows reading ニコニコ漫画 119, キミコミ 29, ニコニコ漫画 16. Two rows carry the same
platform name and nothing tells them apart, while the site calls them `田所さん` and `田所さん（２）`.

The capture holds it. `data/source/nicovideo/nicovideo.yaml` records `work_title: 田所さん（２）`
against comic/55102, and `series[].sources[]` keeps the address and not the name, so the store's
`offer` has nowhere to get it. Representing every listing is what the ruling asks for, and two rows
a reader cannot distinguish represent them only in the arithmetic.

The fix is small and it is a change to the build rather than to the store: carry the listing's own
title into `sources[]`, and `offer` grows a column for it. Deferred here rather than done because
this is pipeline work, which STORE-PLAN §9 keeps out of a maintenance pass.

**AND THE NEWEST LISTING IS THE LIVE ONE.** 不器用ビンボーダンス is still updating in the third of
its three, so a work's state belongs to its most recent listing rather than to the longest or the
first. 470 of the 471 ニコニコ offers state no latest date, so nothing in `offer` can currently
say which listing is the live one; the work's state is decided elsewhere and this table cannot
corroborate it.

## `feed/names.json` is keyed two ways and the site can only read one. Found 2026-08-13

STORE-PLAN §5 loaded the renderings and one publisher's romanisation went missing on the way in.
The cause is in the emitter. `app.js` reaches every entry in this file through `foldKey`, which is
NFKC with spaces removed, and 62 of 386 publisher keys and 112 of 399 imprint keys hold a space
that NFKC keeps. Those entries cannot be looked up by anything the site does.

24 publisher keys collapse onto 12 folded keys, and 5 of those pairs hold different things:

    いんどの宮殿！            en: Indo no Kyuden!, basis: romaji, id: h00097
    いんどの宮殿!            id: h00097

The reader's lookup folds the name and lands on the SECOND, which carries an identifier and no
English. So the English is emitted, shipped in a 3.8 MB file every visit loads, and unreachable.
`スイートピー&COCOA BREAK` and `スタジオぷち屋 桜那えいか、` are the same shape.

**IT IS NOT VISIBLE FROM EITHER SIDE ALONE**, which is why it survived. The build writes both keys
and can see nothing wrong with either; the interface asks for a folded key and gets an answer, so
nothing looks missing. Setting the file beside a store keyed on one fold is what made the pair
show up as a row that would not insert twice.

**THE STORE PREFERS THE ENTRY THE SITE CAN REACH**, which is what `relational.entries` does, so
the store now holds what a reader holds rather than whichever spelling the emitter wrote first.
That is a workaround. The fix is that the emitter should fold its keys, and it is pipeline work,
which STORE-PLAN §9 keeps out of a maintenance pass.

Titles, authors, credit lines, `floor` and `phrases` are all clean, with 0 unfolded keys between
them. It is the two maps written by a different route that differ.

## 660 divisions state their source in prose and no basis. Found 2026-08-13

`reading_boundary` holds a sentence: `the kana in its own surface`, `the National Diet Library's
author heading on record R100000002-I034558058`, `a reviewer's own reading of the whole name,
argued in reading_note`. 680 records carry one and 20 of them also carry
`reading_boundary_basis`, which is the field a query can act on.

STORE-PLAN §5 loads a `division` claim only for those 20, because `claim.basis` is a foreign key
into a closed vocabulary and reading a basis out of a sentence would be a ruling made in a loader.
The other 660 divisions are in the corpus, are shown to readers, and cannot be counted by basis.

**IT IS THE SAME SHAPE AS THE FAULT `claim` WAS BUILT FOR**: 293 divisions sat in `reading_note`
prose while `reading_boundary` was empty, which is why the schema holds one claim per row. The
prose field outlived the fix, and filling `reading_boundary_basis` from it is a naming pass's work
rather than a schema change.

## 18 English titles a reader is served come from no name-store row. Found 2026-08-13

Measured while checking that the store can reproduce what the site serves: 3,186 titles ship an
English name, the store answers 3,168 of them from a claim, and 18 are the build's own derivation.
Two kinds. `RoomforHoneys` and `TheDayTomorrowComes` are already in Latin, so the title IS the
English. `恋愛遺伝子XX:完全版` and `犬も歩けば姫に当たる【電子単行本】` are a base title plus an
edition marker, which `EDITION_EN` glosses beside the base work's name.

Both are derivable from what the store holds, since the base title and the surface are both in it,
and neither is a name anybody curated. Recorded because §1's budget measures derivability and this
is the residue that only emission can settle, which is STORE-PLAN §6.

## A basis nothing has ruled on, and a ruling the table predates. Found 2026-08-13, corrected

**WHAT THIS ENTRY FIRST SAID WAS WRONG AND THE CORRECTION IS THE ENTRY.** It claimed `stated` is an
English basis with no attribution row, on the strength of `ATTRIBUTION` being read too quickly.
`ATTRIBUTION` carries all five English bases including `stated`, and the 194 records it named are
self-sourced titles already written in Latin, which owe no document at all. STORE-PLAN §5a found
the error by asserting it in a test and watching the test fail.

The gap that is real is `back-converted`. It sits in `facts/division.BASES`, `provenance.SOURCED`
lists it among the bases that owe a document, and `READING_ATTRIBUTION` has never carried a row for
it. So 22 readings rest on a basis nothing can say anything about: no kind of source is admitted for
it, which means no kind can be refused either. Either it is ruled on or it stops being a basis.

**AND ONE RULING THE TABLE PREDATES.** `ATTRIBUTION` admits `derived` for `romaji` and nothing
else, and the project owner ruled on 2026-08-09 that Wikidata may be used to raise the floor on a
romanisation. 102 English names now rest on `romaji` with a `community-db` source, which is that
ruling carried out, against a table written before it. `claims whose evidence their basis does not
admit` counts those 102 along with 2 publisher names on `official-jp` citing the national library
and 1 kana surface citing a platform. The composite key goes on `claim` when the number is 0.

## Two pairs of works that were one work each. Found and merged 2026-08-13

STORE-PLAN §5f found `volume_isbn` keyed on the ISBN as a STRING, so 940 of 3,371 hyphenated
spellings sit beside 2,423 bare ones and "one ISBN is one book" is defeated by a hyphen. Normalising
the key is that section's. What normalising REVEALS is this entry: 8 bare ISBNs reach two different
works, and they fall into two pairs.

    w01245  ゆりてつ                          w01603  ゆりてつ～私立百合ヶ咲女子高鉄道部～
    w01463  どうしたら幼馴染♀の彼女になれますか!?   w02055  どうしたら幼馴染の彼女になれますか!?

The first pair shares a credit, 松山せいじ, all four of its books, and a first publication five days
apart. The second differs by one character and shares five books. A third work, `w01376`, holds one
book as two volume rows.

**THE PROJECT OWNER RULED, 2026-08-13:** an ISBN identifies a work by definition, so one reaching
two works means an invariant or the data is broken. Both were. `w01603` is merged into `w01245` and
`w02055` into `w01463`, with the ISBN evidence written into `data/identity/works.yaml`, and the
normalised key is in the schema so the next one cannot enter rather than being noticed later.

**WHAT THE MERGE COST, recorded because a rise is never edited away.** Two budgets moved:
`volume numbers a page draws twice` 5 to 10 and `works holding more volumes than the shop states`
25 to 26. Each merge brings two catalogues onto one row, and MADB dates ゆりてつ's first three
volumes to the 24th of their months where BOOK☆WALKER says the 19th. `merge_volumes` keeps rows
apart when their dates disagree, which is right: which catalogue is correct is not a question a
string comparison answers. The work pages draw those volumes twice until somebody settles the
dates, and that is §9's.

That is the argument for the key rather than a cost of it. The ISBN is the only cross-work book
identity the store has. Normalised, it stops being a spelling and becomes the best duplicate-work
detector this project owns, which is worth more than the constraint it was adopted for.

## A release id still carries the route that captured it. Found 2026-08-13

`platform` is keyed on the display name because six of them arrive under two capture slugs, and the
comment says a platform is identified by its name and not by the adapter that read it. `release.id`
is then the platform's own id, except that it is not: the ids read `comicfuz:` and `comicfuz-free:`,
`sundaywebry:` and `sunday_webry:` and `backfill:`, `ichicomi:` and `ichijinsha:` and
`claim-resolved:`. Thirteen platforms carry two or three routes inside the primary key of `release`.

So the adapter was taken out of `platform` and left in the key of the table that references it. One
event captured twice by two routes would be two rows and the key would not stop it. Measured, that
has not happened: no url appears under two routes, and `(platform, work, instalment, published)` is
unique across all 961 rows. Recorded because the comment is false today and the cost is latent.

## A work merge takes credit edges with it. Found 2026-08-13

STORE-PLAN §6 moved `credits.json` to the store and the edge count came out 5 higher than the file
the compiler wrote. The cause is a chain nothing follows. `data/identity/credit-works.yaml` names a
credit's works by the identifier they had when the edge was recorded, and `credit_page_data` filtered
those against the works that ship. So when a work is merged, its retired identifier stops shipping,
the filter drops the edge, and the person's page loses a work it is named on.

Two of the merges are §5f's own, `w01603` into `w01245` and `w02055` into `w01463`, which is how this
surfaced: resolving each retired identifier through `superseded` adds the 5 edges back.

**THE STORE COPIES THE FAULT ON PURPOSE, FOR NOW.** §6's discipline is that a domain moves by
emitting what the compiler produced and proving it byte for byte, because an emitter that produces
something ALMOST the same is a second producer with a bug. Changing what a credit page shows is a
separate change with its own reason, and it wants a decision: whether an edge recorded against a
retired identifier follows the merge, or whether the registry should be rewritten when a merge lands
so the edge names the survivor directly. The second is tidier and touches a file people edit by hand.

## The store's division of a byline depends on rulings only build.py holds. Found 2026-08-13

STORE-PLAN §6 moved `index.json` to the store and a rebuild produced 6 rows the compiler did not.
`record_credit` holds `facts/credit.split_detail`'s division of a record's creator field, and that
splitter answers differently depending on the INTERPUNCT RULINGS: whether `・` in a given field
separates two people or is a character in one person's name. `くろば・Ｕ` is one artist and
`るいす・まくられん` is two, and nothing about either string says which.

`build.py` derives those rulings from the corpus at run time, hands them to `facts/credit` in
memory, and never writes them down. `data/identity/interpunct-rulings.yaml` exists and holds
`rulings: {}`. So a store built by the compiler has them and a store built by
`adapters/relational/__init__.py --build` does not, and the two divide 6 records differently.

**IT MATTERS MOST WHERE IT IS HARDEST TO SEE.** `equivalent()` rebuilds from source and sets the
result beside a store that has only ever been updated, which is §7's whole check on the incremental
path. A rebuild that divides bylines differently from the compiler will report a divergence caused by
the rulings while somebody spends a morning looking for it in the updater.

**THE FIX IS TO PERSIST WHAT IS DERIVED**, into the file that already exists for it, so both paths
read one answer. That is a change to the build rather than to the store, so it is documented here.
Until then `test_emit` asserts every field of `index.json` except the one the rulings reach, and
says why.

## A published release can leave its month, and a published release can vanish

Found 2026-08-14, by the guard in the site's build refusing to drop three rows from `feed/2026-07.json`.

**TWO ROWS MOVED MONTH BECAUSE THE LEDGER LEARNED THEM LATE.** `comicfuz:78983` and `78986` were
served in July's archive from 2026-08-02, both with `feed_date` equal to their publication date
because the first-sighting ledger held no entry for them. The ledger gained their key on 2026-08-07,
and a row's month follows `feed_date`, so they now claim August and leave the month they were
published in. The archive is itself proof of an earlier sighting: a row served on 2026-08-02 was
seen no later than that, and the ledger says 2026-08-07. Either the ledger's date is corrected to
what the archive proves, or July is regenerated deliberately and the rows move with that said out
loud. The ledger cannot see the archive, because §11 leaves the published files in the other
repository, so the owner decides and no pass can.

**AND ONE ROW IS SIMPLY GONE.** `pixivcomic:…:Step.13② されど花は枯れず` is in the published July
archive and in no source the corpus now holds. Under the old arrangement the archive file kept it
because the file was kept; §6 made the file derived and §7 made the store forget what a capture
stops returning, so a release nobody captures again is a release the store drops and the archive
loses. That is a real change in what "a published update does not stop having happened" can mean,
and the choice it forces is whether `release` is append-only with a mark for what is no longer
listed, or whether an archive may lose a row when its source does.

## The month a run happens in had no archive, and 246 published updates went through the hole

Found 2026-08-30. The procedure is fixed; 141 rows are recoverable and undecided.

**WHAT THE HOLE WAS.** `feed/current.json` is a 14-day window, and a month was archived only once it
had ended. So a row published on 3 August left the window on 17 August and entered no other file
until September. For up to seventeen days it was in the store and served to nobody.

**WHY THAT ERASED RECORDS RATHER THAN MERELY HIDING THEM.** The site carries forward the rows a
published file holds, which is what the owner asked for on 2026-08-29 after July lost rows. A row in
no file has nothing to carry it. So when the store stopped stating one of these, as it does whenever
ニコニコ re-mints a work-level id or マンガよもんが expires a chapter, the row was gone with no
record it had existed. 427 August rows were unreachable when this was measured and 246 more had
already gone that way.

**THE EXCLUSION OUTLIVED ITS REASON.** Both producers said the same thing: writing an unfinished
month would either publish it incomplete or require rewriting it tomorrow, "and rewriting is the one
thing an archive may not do". The owner retired that on 2026-08-11. A month locks its ROW SET and
not its bytes, and every published month is already rewritten on every build. The rule the exclusion
rested on was gone and the exclusion stayed.

**FIXED BY PUBLISHING THE MONTH IN PROGRESS**, so a row enters an archive the day it is published
and the carry-forward covers it from that day. `emit.archived_months` is now the one producer of
which months are archived; `build.py` asks it instead of stating the rule a second time, which is
how the two came to disagree with the store's side of the argument in the first place.
`adapters/relational/test_emit.py` pins the ceiling as inclusive, because it reads like an
off-by-one to anyone who has not lost 246 rows to it.

**WHAT IS NOT DECIDED, and why it is not a restore.** 105 of the 246 are still published under an id
that changed when a platform slug or an address format did, `remaining` to `comic-zenon` and
`corocoro` to `corocoro-online`; restoring those would show a chapter twice, and seven would file a
July chapter under August. The remaining 141 are in `data/queue/archive-recovery-2026-08.yaml`, and
they are not one class either: 44 dated 2026-08-13 are consecutive chapters of one comic-fuz series,
which is a back catalogue read for the first time rather than six chapters published in a day, and
25 sit in the 2026-08-07 bucket `build.py` itself flags as bulk re-dating. Restoring those would
assert updates that did not happen. Each row needs a reading, which is the slow half; the rows are
kept so that losing the evidence is not how the deliberation ends.

**RELATED.** `A published release can leave its month, and a published release can vanish` above is
the same subject from the other side, and it stands: this closes the route by which a row was never
filed at all, and says nothing about whether `release` should be append-only.

## The pass that mints an identifier cannot see the works that lack one

**PARTLY CLOSED 2026-08-31, and the cause was not where this entry put it.** 16 of the 49 were
works the corpus already held, kept out by a lookup that never read the address it was given. See
the entry below. 33 remain and they are the genuinely new works, which still need minting and still
need a person, so everything this entry says about append-only assignment stands.


Found 2026-08-31, working the induction half of a maintenance pass. 49 works reach no reader.

**THE LOOP.** `build.py` compiles a series row for every work a capture reached. A row with no
identifier becomes no `work` row in the store, which the run has said out loud since the day the
store arrived: "A WORK WITH NO IDENTIFIER REACHES NO READER". `facts/identity` is what mints one,
and under §13 it reads its population from the STORE. So a work with no identifier is absent from
the store, absent from the population the minter reads, and never minted. It is the minter sharing
its subject's blind spot, which is the fault STANDING-INSTRUCTIONS §14b names for CHECKS, arriving
in a pass that was supposed to fix the thing.

**MEASURED.** `population.series(None)` returns 3,036 rows and holds none of キジとイナサ,
私の彼女はボディビルダー, 骨に願いを、星に呪いを or 贋作の第十番, which are four of the 49 the same
build reports as awaiting an identifier. A work already carrying an id from a print record, ゆるゆり
and 大室家 among them, IS visible, which is the loop stated from the other side: sight depends on
the very thing the pass would supply.

**WHAT IT COSTS.** 49 works are compiled, named, dated and then dropped: no work row, no page, no
entry in the works list, no search. 29 of them also publish updates a reader can see, which is what
`updates naming a work we do not hold` counts, at 76 rows today. The number rises by roughly one
work a day.

**WHAT IS NOT THE CAUSE, each ruled out by measurement rather than by argument.** The target list
already holds 25 of the 28: they are admitted, fetched and captured, and カドコミ's
`chapters.yaml` carries a full `web_work_chapters` record for 私の彼女はボディビルダー with its
label and tags. `data/queue/address-work-level-gigaviewer.yaml` was 20 days stale and refreshing it
changed nothing: the assignment mints 10 either way. Running the assignment as it stands does not
help the 49 at all and raises `one work under two names in a list` from 3 to 11, because the 10 it
mints are contested rows gaining a SECOND identifier for a work already held. That was tried and
reverted.

**WHY THIS IS NOT A MAINTENANCE PASS'S TO CLOSE.** Assignment is append-only and
`facts/identity/BLINDSPOT.md` is plain about the consequence: a wrongly minted identifier cannot be
withdrawn, only retired. Minting 49 unexamined would repeat, permanently, the duplication the
10-row attempt above produced reversibly. The route is to give the minter sight of the rows that
lack an identifier, `--series` already reads a file rather than the store, and then to separate the
genuinely new works from those already held under another anchor before anything is minted. The
separation is the half that needs a person.

**TWO SMALLER THINGS FOUND ON THE WAY.** `adapters/gigaviewer/workaddress.py` and
`facts/identity` run in NO workflow: the registry was last written on 2026-08-13 and the joins file
on 2026-08-10, so nothing has minted an identifier for eighteen days. And 13 platform slugs the
feed carries are absent from the register, `ganganonline` against its `gangan-online` and
`www-comic-essay-com` against its `comic-essay` among them, carrying 130 rows. The reader is
unaffected, `plat_name` being correct on every one, but `platform.serves_openly` answers False for a
platform the register does hold, so `admit` would refuse a candidate from it.

## The work-level address was captured, stored, and never looked up

Found 2026-08-31. 16 works reached no reader because of it, and it is fixed.

**WHAT WAS ALREADY THERE.** `build.py` computes `series_address` into the row's `series_url`, from
the captures `gigaviewer/workaddress.py` reads; that pass fetches a chapter page, follows the atom
link the platform puts on it, and confirms the og:title names the same work. The registry holds 506
feed addresses and 337 reader addresses that came from exactly there. Both halves were built for
this, deliberately, and documented at both ends.

**WHAT NOTHING DID.** `identity.for_row` tried the row's headline and each of its sources, and never
`series_url`. Measured: of the 843 work-level anchors in the registry, not one appears among the
1,796 addresses the rows carry. So every one of them was dead the day it was written.

**WHY IT COST WHOLE WORKS.** A GigaViewer headline is a chapter address, and `stable_url` cannot
reduce `ichicomi.com/episode/<opaque>` because the series id is nowhere in the string. So the lookup
key changed every time a work published, the registry had never seen it, the row got no identifier,
and a row with no identifier becomes no work row. w00145 shows the shape from the other side: it has
accumulated three ichicomi chapter anchors from three different runs, one per publication, plus the
atom anchor that would have settled it.

**A WORK SURVIVED ONLY BY BEING SOMEWHERE ELSE.** ささやくように恋を唄う keeps its identifier through
pixivコミック's `works/5758` and ニコニコ's `comic/56012`, which are work-level addresses. A work
serialising ONLY on a GigaViewer instance had nothing stable at all, which is why ゆるゆり and 大室家
were among the missing.

**THE FIX IS ONE ADDRESS ADDED TO THE LOOKUP, LAST.** Last is what makes it additive: a better
anchor consulted first would move rows that resolve today, and an identifier that moves is a
published address that stops resolving. Proved rather than argued, by building both ways and
comparing all 1,424 rows: 16 gained an identifier, 0 moved, 0 were lost. `one row per identifier`
holds, `one work under two names in a list` stays at 3, and `updates naming a work we do not hold`
falls 76 to 57.

**WHAT IT DID NOT REACH, AND WHAT CLOSED IT.** The 33 works with no identifier anywhere were minted
on 2026-09-01 at the project owner's instruction: 29 new identifiers, 3 anchors attached to works
the corpus already held, and one pair of rows that turned out to be one work. Every row now carries
an identifier, 1,423 of 1,423, and the run no longer prints `awaiting an identifier` at all.

**THREE OF THE 33 WOULD HAVE SPLIT A WORK IN TWO, and finding them took two tries.** A check on
folded titles found nothing, because a print-only registry entry carries `title: None` and is
reachable only through its `madb:` anchor; those were 3分待って むぎ先輩 against w02200 and
さざめとりお against w01998. The third, 新米錬金術師の店舗経営 against w01987, survived even that and
was caught by the gate: `one work named two ways across its rows` went 0 to 1, because the
cataloguer's シリーズ suffix keeps the two titles from folding together and that budget strips it.
Each is attached with its evidence rather than minted, and each rests on a shared credit as well as
a shared title.

**THE LESSON IS THE SHAPE OF THE CHECK.** A registry entry with no title cannot be found by title,
so a duplicate check reading the registry alone is blind to exactly the entries a print-only work
leaves. The check that worked reads the shipped index, where the print record carries its title.

## A discovery source that times out takes the other one with it, and the run reports success

Found 2026-08-31, in run 33409338399.

**WHAT HAPPENED.** `yurinavi/discover.py` hit `urlopen error timed out` on its first fetch. The step
runs both discovery passes under one `bash -e`, so `webcomics/coverage.py` never started, and the
step carries `continue-on-error: true`, so the job went green. The run committed no change to
`data/queue/yurinavi.yaml` or `data/coverage/`, which is how it was found; `gh run view` reports the
step as `success` on all four of the last runs, so the outside view cannot distinguish a run that
discovered nothing from one that discovered nothing new.

**WHY THE COUPLING IS THE WORSE HALF.** The two passes read different sites and answer different
questions, and `coverage.py` is what merges an admitted candidate into the target list every
platform adapter reads. So one comparator being slow costs the run its whole intake, including the
admission policy of 2026-08-15. `update.yml` already argues this exact case for Stage A, "ONE
ADAPTER MUST NOT COST THE NIGHT", and Stage 0 was written before that argument and never got it.

**IT HAPPENED TWICE, AND IT STARTED TODAY.** Both of 2026-08-31's runs died the same way, on
`https://yurinavi.com/feed` with a 45-second timeout, while 28, 29 and 30 August carry no failure in
that step at all. From here the feed answers in 1.5 seconds: a 301 to `/feed/` and then 200
`application/rss+xml`. So the source is up and something between it and a GitHub runner is not,
which is a different problem from a slow morning and is not one the next run necessarily fixes.
Two days of intake are the cost so far. What compounds it is that the record says success either
way, so nobody would have looked.

**THE SHAPE OF THE FIX.** Two steps rather than one, or each command allowed to fail on its own, so
a timeout costs one source instead of both; and something that reports what discovery actually did,
since `continue-on-error` is right here and hiding the outcome is not.

## The work-address pass resolves an address and then cannot say whose it is

Found 2026-09-01, running `gigaviewer/workaddress.py` after 30 works were minted.

**WHAT IT REPORTS.** `{'resolved': 503, 'reader': 336, 'no-identifier': 20, 'no-series': 8}`. The 20
are ichicomi rows whose series address it read successfully and then wrote to the unresolved file
instead of the joins file, because it could not name the work the address belongs to. ゆるゆり,
大室家, 骨に願いを、星に呪いを and seventeen more are in that list, and every one of them now carries
an identifier.

It looks the work up by the row's own address, which on these platforms is a chapter address, and
that is precisely the address resolving to nothing. So the pass written to repair moving anchors is
defeated by the moving anchor. The row it is already holding states its identifier, and asking the
row would close all twenty.

**THE OTHER EIGHT ARE A DIFFERENT STATE and are no fault of this pass.** `no-series` means the
chapter page carries no atom link to follow: four ヒーローズウェブ rows, one チャンピオンクロス, one
コミックエッセイ劇場, one ヤングアニマルWeb and 阿佐ヶ谷サキュバス同人物語. Those works have no
work-level address to find, which is what `rows with a moving address` counts, now at 9.

## Eighteen of the nineteen per-series feeds had been frozen for a month

Found 2026-09-02, working the induction half of a maintenance pass. Thawed; the minting behind it
is not done.

**WHY IT MATTERED.** A platform-wide feed states a CHAPTER address, and `identity.stable_url`
cannot reduce a GigaViewer one to the work. The per-series feed states `/atom/series/<id>`, which
does not move, and its records are `web_work_chapters`, the record type `build.py` turns into a
work row. So a work reached only by the platform-wide feed publishes updates for ever and never
becomes a work: eleven of them on 2026-09-01, which `updates naming a work we do not hold` counts.

**WHY IT WAS FROZEN.** `stage-a.yaml` ran `series_feeds.py` for ichicomi alone, under a note saying
the other platforms "exit immediately and always have". That was true of the form it was written
in: without `--candidates` a platform must declare `series_pages`, which in practice only ichicomi
does. WITH `--candidates` the pass takes its targets from the list every other adapter already
reads. Run by hand against となりのヤングジャンプ it resolved 87 series and wrote 87 work records
against a file last touched on 2026-08-02.

**WHAT THE THAW COST AND BROUGHT.** Six platforms run by hand: 306 series and 3,686 episodes, of
which コミックDAYS alone was 110 series and 2,989 episodes and took about 25 minutes. Stage A runs
six adapters at a time, so nineteen of these add roughly a third of an hour of wall clock rather
than the sum. Each entry is `optional`, so a platform that fails costs its own records.

**THE ROUTE THAT WORKS, END TO END.** A work seen only in a platform's own feed is written into
`data/queue/feed-discovered.yaml` as a discovery candidate; `admit` takes it under the standing
ruling of 2026-08-15; `coverage.py` merges it into the target list; `series_feeds.py` resolves its
episode address to a series feed and writes a `web_work_chapters` record; `build.py` makes a work
row. Nine works were carried through that on 2026-09-02 and gained rows.

**WHAT STOPS THERE, AND WHY IT STOPS THERE.** Those rows have no identifier, and the assignment
would mint 38 while reporting 30 CONTESTED anchors, each one a web row whose print anchor another
work already holds: かわいい同盟 against w00313, ロックは淑女の嗜みでして against w00432,
この恋を星には願わない against w00372. Minting is append-only. Running it as it stands would create
a second identifier for works the corpus already holds, which is the duplication a smaller version
of this produced on 2026-08-31 and had to be reverted. Refreshing the joins file first does not
change the count, which was tried. The contested set wants attaching one at a time with a basis,
and that is a person's call rather than a pass's.

## The minter and the lookup disagree about which address names a work

Found 2026-09-02, narrowing the reason the 15 idless works cannot simply be minted. Not fixed, and
the reason it is not fixed is in the last paragraph.

**THE TWO HALVES.** `identity.for_row` is what `build.py` asks, and it tries every address a row
holds: its headline, each of its sources, and its work-level address. `identity.assign` is what
mints, and it keys on ONE, `web_anchor(row.url)`, the headline alone. So a row whose identifier the
build finds perfectly well is a row the minter believes it has never seen, and it mints a second
identifier for a work already held.

**MEASURED.** A dry run mints 38 and reports 30 contested anchors. Every contested one is the same
shape: an existing work and a would-be new id under the SAME title, ゆるゆり as w00174 and w03282,
大室家 as w00150 and w03283, 私の百合はお仕事です! as w00164 and w03284. In each case the registry
title matches the row's title exactly and the row's headline anchor, today's chapter address, is
held by nobody. One duplicate has already landed: 異種族女子に○○する話's ニコニコ address is held by
w03202 while the work is w00961.

**WHY ATTACHING THE HEADLINE IS NOT THE ANSWER.** `--attach` would bind today's chapter address to
the held id, and a GigaViewer chapter address changes on every publication, so tomorrow presents a
new one and the mint comes back. w00145 shows the treadmill from the other side: three ichicomi
chapter anchors from three runs, one per publication.

**AND WHY THE OBVIOUS CODE CHANGE IS NOT THE ANSWER EITHER.** Making `assign` look a work up by any
anchor is what `assign`'s own docstring refuses, with a worked example: 超深宇宙より愛をこめて is a
serialisation and a 読み切り版, two rows with two URLs, and one MADB record matches both titles, so
lookup by any anchor merges them, and merging is a decision with a basis. That objection is about a
shared PRINT anchor rather than a row's own web addresses, which is the distinction a fix would
have to argue and hold to.

**SO THE SHAPE OF THE FIX IS NARROW.** The identifying anchor for a web row should be its
work-level address where it has one, falling back to its URL, and the fallback has to prefer
whichever is ALREADY held or it will mint against a new key for rows that resolve today. That is a
change to append-only assignment, its blast radius is every work's identity, and it wants proving
the way `for_row` was proved: build both ways and assert that no existing identifier moves. It is
the owner's to take, and until it is taken the minter must not be run, which is why 15 works have
rows and no identifier and reach no reader.
