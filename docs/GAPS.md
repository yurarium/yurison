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

### A date the shop states in its own blurb is a printing (2026-08-08)

**The owner's ruling.** A date コミックシーモア states inside its own description of a work attests
that date. The previous round found these and left them, because nothing said whether a shop
writing a date in prose is the shop stating a fact. It is, and what it states is a PRINTING, so it
outranks the delivery date on the same row under the rule that a print date always wins.

**What the cache holds.** 279 of the 1,833 captured work pages mention a doujin word in the shop's
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
`edition_statement`'s 174 and 79 answers and does move the loose doujin-word count from 284 to 279,
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
