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

## 9. Nobody has looked for the name the person uses

616 author names on the live site are shown as a romanisation we derived from confirmed kana. That
is mechanical and carries no note, correctly. What it hides is that we never asked whether the
person writes their own name in Latin script.

A minority of artists do, and they are not quiet about it. A pen name set in Latin on a creator's
own profile, in the credits of a licensed edition, or on the work's own cover is attestable exactly
the way a splash-art title was: 49 works gained an English title that way on 2026-08-04, from art
we had been sitting on.

**The state already exists and has never been reached for people.** `adapters/names/curate.py`
accepts `stated`, documented as "the person's own rendering, where they wrote it", and every author
pass so far has filled `reading` from NDL and openBD without once looking for a Latin form. So the
schema is right, the evidence is out there, and the search has not been run.

What it changes for a reader: a name at `stated` is the person's own and carries nothing of ours,
the way a licensed title does for a work. Today all 616 are ours by default rather than by finding.

Where to look, in the order likely to pay. The licensed editions print a credit, and
`data/queue/english-licences.yaml` already holds 87 licences whose pages carry author credits
nobody has read. Series art and platform profiles are the source that produced the 49 titles, and
the platform ranking in `data/coverage/splash-titles.md` says which are worth opening. The
publisher's own author pages carry the same `publisher-jp` evidence the openBD reading route uses
for kana. Anthology contributor lists name people the shelf captures reach and the corpus does not.

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

**How much the question is worth has not been measured.** The site answers one ISBN in several
minutes under a single-threaded polite fetch, so a sweep of all 49 is hours rather than minutes and
was not run to the end. What was observed by hand: 少女美学 and voiceful, both 一迅社 2006 volumes
that neither MADB nor openBD holds, resolve to a book page stating the publisher and 発行年月日.
Those two are the oldest block, which is the half openBD is weakest on, so the 2024-onward block is
if anything likelier still. Measuring the rest is worth doing only after the terms question is
settled, since a negative answer there makes the number academic.

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
