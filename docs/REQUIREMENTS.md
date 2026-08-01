# Requirements

How records are sourced, validated, built and published.
[DEFINITIONS.md](DEFINITIONS.md) defines what qualifies as a record in the first place.

---

## 1. Source-language firewall

**The database contains only what Japanese sources attest.**

Foreign-language sources (AniList, MangaDex, MangaUpdates, English Wikipedia) may be used to
*discover* candidate works. They may not supply a single stored field. A record whose provenance
points outside the allowlist fails build-time validation.

This is enforced mechanically, not by convention: every field carries a `source` and the build
rejects any value whose source is not on the allowlist.

### Cost, accepted deliberately

Foreign aggregators are where yuri classification is densest. Excluding them means classification
is done from Japanese sources or by hand, so the database grows more slowly and the **discovery
queue is first-class infrastructure** rather than an afterthought: candidate titles enter a queue,
and only acquire a record once Japanese sources are found for them.

### Source tiers

Field-level priority is **A > B > C**. Where tiers disagree, the higher tier wins and the conflict
is recorded rather than discarded.

**Tier A — authoritative** *(verified 2026-08-01)*

| Source | Access | Notes |
|---|---|---|
| 文化庁メディア芸術データベース (MADB) | Bulk JSON-LD + Turtle at [github.com/mediaarts-db/dataset](https://github.com/mediaarts-db/dataset); Web API and SPARQL endpoint | Magazines, issues, volumes, and issue contents. Ships **monthly**; pull from Releases and pin the tag. URIs migrated `bunka.go.jp` → `artmuseums.go.jp` on 2024-11-26. **Issue contents cover only 9.3% of issues and none of the yuri magazines** — see [MADB.md](MADB.md) before planning around it. |
| 国立国会図書館サーチ (NDL Search) | SRU / OpenSearch | Legal deposit — effectively every book printed in Japan, including pre-2000. Coverage no fan database has. |
| openBD | JSON API | ISBN → publisher-supplied bibliographic data and cover images. Strong on in-print and forthcoming, weak historically. Terms obligations in §3. |
| 出版書誌データベース (Books.or.jp) | Web | JPO-run publisher bibliography. |

MADB and NDL cover the historical half; openBD and publisher/platform sources cover the current
half. Neither alone is sufficient.

**Tier B — primary.** Publisher and magazine official sites (一迅社/百合姫, KADOKAWA, 芳文社,
白泉社, ガレット, …) and Japanese web-manga platforms (pixivコミック, ニコニコ静画,
コミックウォーカー, ガンガンONLINE, publisher web magazines).

**Tier C — reference.** Japanese-language reference, tracking and aggregation sites. Content
classification may cite Tier C, since interpretive claims are usually only discussed in fan and
editorial sources, but must record that it did so.

| Source | Value | *(verified 2026-08-01)* |
|---|---|---|
| [百合ナビ](https://yurinavi.com/) | Long-running yuri news site: a news feed, a WEB連載 list, and a 発売日 calendar. Occupies an interesting position in the ecosystem — it is where new yuri work gets announced — but is **not a source of truth**. Inclusion is traditionally loose, dating from a period when far less yuri was published. Valuable for **discovery**; weightless as verification. |
| [Web漫画アンテナ](https://webcomics.jp/tag/%E7%99%BE%E5%90%88) | Cross-platform web-manga aggregator, ~1,530 works under its 百合 tag with platform and update time. Crowd-tagged, so likewise discovery only. |
| 日本語版Wikipedia, pixiv百科事典 | Background and classification **discussion** — see the distinction below |

**Tier D — discovery only, never stored.** Foreign aggregators. Permitted to enqueue a candidate
title. Permitted to supply nothing else.

### Tier is authority; role is what a source is used for

The two are independent, and keeping them apart is what lets Tier C sources be genuinely useful
without polluting the record:

| Role | Meaning | Who |
|---|---|---|
| **Attesting** | Supplies stored bibliographic fields | Tier A and B only |
| **Corroborative** | Supports a classification as `basis` | Tier A–C |
| **Discovery** | Tells us a work exists, nothing more | Any tier, including D |

A source may hold several roles. Two rules follow, and both matter.

> **A third-party tag is never a `marketing_label`.** Web漫画アンテナ or 百合ナビ filing a work
> under 百合 is not a label. `marketing_label` requires publisher- or platform-side labelling
> (DEFINITIONS §4) and nothing else. These sources will tempt exactly this confusion, since a 百合
> tag *looks* like a label.

> **A bare listing is not corroboration either.** Tier C may support a `content_tier` when it
> *says something* — a review, an article, an encyclopaedia entry describing how a work treats its
> relationship. A work merely appearing under a 百合 heading is a bare assertion of membership,
> produced by crowd tagging or by loose editorial inclusion, with no reasoning attached and no way
> to weigh it. Evidence has to state a case; a tag only claims one.
>
> This is why the two coverage yardsticks in §5 are strictly discovery, despite both being
> Japanese and both being about yuri specifically.

### One-shots are the hardest discovery problem

読み切り are works under DEFINITIONS §6, not releases — but they surface in no serialisation
listing, frequently get no 単行本, and are often time-limited. Nothing in Tier A or B reliably
announces them.

Monitoring 百合ナビ's news blog is therefore a **named discovery mechanism**, not incidental
enrichment: it is the practical route to a category that would otherwise be systematically missing
from the database. Web-manga one-shots found this way go straight to archive-at-first-sight (§5),
because they are the records most likely to lose their source.

### The one carve-out: `title_en_official`

Official English titles are the single field where a non-Japanese source is authoritative by
nature — the English licensor is the entity that announces it.

- Sourced from the licensor's own announcement or catalogue
- Flagged `announced` vs `released`
- Marked with its own provenance type, distinguishable from firewall-compliant fields
- Populated in **Claude-guided enrichment passes**, outside the steady-state cron pipeline

This is an explicit, bounded exception. It does not generalise to any other field.

Like all judgment-bearing work, these passes happen **outside the automated pipeline** — see the
steady-state/maintenance split in §6.

---

## 2. Media policy

### Absolute rules

1. **No image files are ever committed to the repository.** Committing a cover means GitHub stores
   and serves a copy — reproduction and distribution, the rights most squarely held by the
   publisher. The realistic risk is not litigation but a DMCA takedown that removes the repository
   or disables Pages, destroying the project rather than trimming it.
2. **No publisher synopsis or あらすじ text is stored.** Marketing blurbs are copyrightable
   literary works. Japan's 引用 exception (Art. 32) will not cover a database of them: quotation
   requires the quoted material to be *subordinate* (主従関係) to one's own content, and a
   database of blurbs inverts that.
3. **Outbound links point only to authorised sources** — publisher sites, official platforms,
   legitimate retailers. Never scanlation or aggregator hosts. Besides being right, this keeps the
   project clear of Japan's リーチサイト規制 (2020 Copyright Act amendment), which targets sites
   specialising in links to infringing copies.

### What is safe to store

Bibliographic **facts** — title, creators, publisher, ISBN, dates, volume counts, magazine,
serialisation run — are not copyrightable. Facts are not works (Japan Art. 10(2); *Feist* in the
US). A database's *arrangement* may attract thin protection as a データベースの著作物 (Art. 12-2),
but extracting individual facts from one does not infringe it.

Titles are too short for copyright. Trademark is a separate axis, and nominative use in a
bibliographic database is precisely what trademark permits.

### Cover images

Referencing a cover by URL leaves the file on the publisher's server; the repository holds a
string. Under the US *server test* (*Perfect 10 v. Amazon*, 9th Cir.) the linker does not display
the work. That test is not universal — the S.D.N.Y. rejected it in *Goldman v. Breitbart*, and the
EU's *Svensson*/*GS Media* line distinguishes sharply between authorised and unauthorised targets.

Rather than rely on any of that, the rule is narrower and rests on permission:

> **Reference cover images only where a Japanese source distributes them for reuse — openBD in
> practice. Never scraped from publisher marketing pages.**

openBD's covers are supplied by publishers through JPO/版元ドットコム for exactly this purpose.
A cover scraped off a marketing page has no such implied licence, and will often break anyway,
since Japanese publisher sites commonly block cross-origin image requests.

Implementation: lazy-loaded, with a graceful **text fallback** when blocked or missing;
**suppressed entirely** on `explicit_content: true` records.

> **This yields almost nothing in practice (measured 2026-08-01).** Across the 646 ISBNs of the
> Phase 1 corpus, openBD resolved 498 and supplied **one** cover image. 一迅社 does not feed cover
> art to openBD, including for December 2025 releases. The rule above is correct and stays, but the
> site is **effectively text-only** for this corpus.
>
> The tempting fix — pulling covers from the publisher's own product pages — is forbidden by the
> rule above and is not a matter of degree: a scraped marketing image carries no reuse permission,
> which is the entire basis on which openBD's are usable. If covers matter enough, the answer is
> another publisher-supplied feed, not a relaxation here.

---

## 3. Obligations imposed by source terms

These are not preferences. They follow from terms verified on 2026-08-01.

### openBD

> 「openBD APIが提供する書誌・書影・内容紹介・書評情報などすべての情報は、本の販促・紹介目的に限り
> 使用できます。」

Free to use, including 書影, **for book promotion and introduction purposes**. A bibliographic
discovery database is a 紹介 purpose. Three obligations follow with real design consequences:

1. **Data must not be arbitrarily modified** (`任意に改変してはいけません`). Corrections may not
   be written back onto openBD values as though they were openBD's. This makes the layered
   architecture (§6) a *requirement*, not a preference: openBD values are stored as fetched, and
   curation lives in a separate overlay with its own provenance.
2. **Deletions and changes must be reflected promptly.** The refresh cron is a terms obligation,
   not merely a feature. It also argues for referencing covers live rather than caching them, so
   that removals propagate on their own. This obligation attaches to openBD's *content*, not to
   the underlying fact of publication — see §4, which is where that distinction is drawn.
3. **The right to use API-obtained information may not be lent, transferred or sold to third
   parties.** This plainly prohibits reselling access. Whether it constrains republishing a bulk
   openBD-derived dataset as a standalone download is genuinely unclear — so **do not publish a
   bulk openBD field dump.** The site itself, as a 紹介 interface, is unproblematic.

openBD may change its terms or discontinue service without notice. Do not build a single point of
failure on it.

### MADB

Free secondary use, subject to: noting where data has been edited or processed, retaining the
notice that the data is openly reusable, respecting creators and related communities, observing
non-copyright rights, and citing the dataset version in academic use. **Record the MADB dataset
version used in every derived record.**

### Takedown posture

The repository carries a documented takedown policy and contact from day one, with a standing rule
that **any contested record or reference is removed immediately on request, without argument.**
The purpose is to protect the project and the account, not any individual record.

---

## 4. Archival integrity — the record persists

**A work's publication is a historical fact. It is never removed from this database because a
source stopped carrying it.**

Commercial bibliographic databases are inventories, not archives. openBD drops out-of-print
titles; platforms delist works when serialisation ends; publisher sites are rebuilt and lose their
back catalogue. Every one of those is a change in what a source *currently sells or serves* — none
is evidence that the work was never published. A database that mirrors its sources' deletions
inherits their amnesia, and for the historical half of this project that would be fatal.

### Resolving the tension with openBD's deletion term

§3 requires openBD deletions to be reflected promptly. That obligation attaches to **openBD's
content** — its data payload, 内容紹介, 書評, and above all 書影. It does not attach to the
underlying fact that a book was published, which is uncopyrightable (§2) and not openBD's to
retract from the world.

Both are therefore satisfied at once:

| On deletion at source | Action |
|---|---|
| Cover image | Stops rendering automatically — covers are referenced live, never cached |
| Source-supplied payload (synopses, reviews, their record as such) | Marked withdrawn; no longer presented as current data from that source |
| Bibliographic fact — title, creators, publisher, ISBN, dates, serialisation | **Retained**, with its provenance moved to a withdrawn state |

### Provenance is a lifecycle, not a timestamp

Every attested field carries `first_seen`, `last_confirmed`, `withdrawn_at`, and

```
attestation_state ∈ { current, withdrawn-at-source, superseded }
```

A withdrawn fact is still displayed. It is displayed *as* a fact once attested and no longer
carried, with the date it was last confirmed — which is more informative than either deleting it
or pretending the source still stands behind it.

### Disappearance is not a single event

Three cases need different handling, and conflating them is precisely how an archive enshrines its
own errors:

| Case | Meaning | Handling |
|---|---|---|
| **Correction** | The source fixed an error; our stored value was wrong | `superseded` — the new value becomes current. The old one stays in history but is **not** preserved as fact. |
| **Withdrawal** | Out of print, delisted, licence lapsed, platform closed | `withdrawn-at-source` — the value stands as historical fact |
| **Retraction** | Pulled over a rights dispute or at an author's request | `withdrawn-at-source`, flagged for human review — the takedown policy may apply |

Correction and withdrawal are distinguished by whether a *replacement* value appeared alongside
the disappearance. Where that is ambiguous, the pipeline flags for review rather than guessing —
guessing wrong in the correction direction means permanently preserving an error as history.

### Pipeline rule: merge-and-mark, never replace-and-drop

**Absence of a record in a refresh is never an instruction to delete.** Full-replace semantics are
forbidden outright. A refresh may add, may supersede with evidence, and may mark withdrawn. It may
not remove. This is the single most important invariant in the pipeline and is enforced in
validation (§6).

### This does not override a takedown

The persistence principle governs **source-database churn**. It does not override a rightsholder's
request under §3. openBD dropping a title and a publisher demanding removal are different actors
with different standing: the first is inventory churn and the fact survives; the second is honoured
immediately and without argument.

### Capture must be self-sufficient

Because a record may outlive every source that attested it, evidence has to be good enough *at
capture time* to stand alone afterwards: normalised facts, retrieval timestamp, and an archive URL
captured **at first sight** rather than resolved lazily later. By the time a source disappears it
is too late to improve the record of it.

Git supplies the deeper archive at no cost — the full history of the source layer is recoverable
from the repository, so every state a source was ever seen in remains inspectable. But git history
is not queryable by a static site, so withdrawn state is also materialised into the current
records.

MADB dataset versions are pinned rather than floating, and diffs between versions are themselves
evidence of correction versus withdrawal.

---

## 5. Release tracking (web manga)

For web manga with `status: ongoing`, the database tracks **releases** as well as works: the
individual chapters and chapter-like items a serialisation channel emits.

### A release is not a work

Works are the unit of inclusion (DEFINITIONS §2). Releases hang beneath them and are never
independently classified, never independently included or excluded. A one-shot published in an
anthology is a *work*; chapter 43 of an ongoing serial is a *release*.

### What counts as a release

The criterion is deliberately wide: **anything the serialisation channel publishes into the slot
where a chapter would appear.** Filtering to "real chapters only" would discard exactly the signal
that tells you what is happening to a series.

| `release_type` | Examples |
|---|---|
| `chapter` | A regular numbered instalment (第○話) |
| `chapter-extra` | 番外編, 特別編, 出張版 |
| `bonus` | おまけ, 4コマ, post-chapter extras |
| `notice` | 休載のお知らせ, schedule changes, move to another platform |
| `apology-art` | The illustration posted in place of a missed chapter |
| `announcement` | 単行本 release notices, adaptation announcements |
| `republication` | 再掲 and reruns |

Each release also carries `advances_narrative: bool`. This is what separates "when did this series
last *update*" from "when did this series last publish *story*" — an apology illustration means the
series is alive but stalled, which is real information and is lost if such posts are discarded. Both
questions are answerable only if quasi-chapters are recorded and typed rather than filtered out.

### Three separate axes

Attestation, availability and access are distinct, and conflating any pair of them is the obvious
mistake:

- **`attestation_state`** (§4) — does a source still attest that this release happened?
- **`availability`** — is it reachable at all?
- **`access`** — on what terms can it be read?

```
availability ∈ { available, expired, unavailable }
```

`expired` is the common and *expected* case on Japanese platforms, which routinely publish under
期間限定公開 and then display 公開終了 or similar. That is an announced end to a publication window,
not a disappearance: the platform still confirms the release happened. `unavailable` is silent
removal. A release can perfectly well be `attestation_state: current` and `availability: expired`.

### Access terms

For releases that are `available`, the terms of reading are recorded. This is **multi-valued**,
because Japanese platforms routinely offer the same chapter on several terms at once — most
commonly 待てば無料 alongside an option to pay to read immediately.

```
access_modes ⊆ { free, free-account, free-timed, subscription, purchase }
```

| Mode | Typical labelling | Meaning |
|---|---|---|
| `free` | 無料公開, 全話無料 | Readable with no account |
| `free-account` | 会員無料, ログインで無料 | Readable with a free account |
| `free-timed` | 待てば無料, チケット, ポイント回復 | Free but rate-limited — a wait or ticket gate. Records `wait_hours` where the platform states it. |
| `subscription` | 読み放題 | Included in a paid subscription |
| `purchase` | 単話購入, コイン/ポイント | Paid per chapter |

This makes "what can I read for nothing right now" a first-class query, which is probably the most
useful thing this half of the database can answer.

**Access is the most volatile field in the project.** A chapter is commonly free for one or two
weeks and then flips to `purchase`. Three consequences:

1. Every observation carries `access_observed_at`, and the field is **never displayed without its
   freshness**. Past a staleness threshold the interface degrades from asserting "free" to
   reporting "last seen free on ⟨date⟩" — a stale access claim is worse than none, because it
   sends readers to a paywall.
2. Access history is retained under §4's append-and-mark rule. "Free until 2026-07-14" is itself
   historical information about how a work was published, and is not overwritten.
3. Access volatility, not chapter cadence, is what sets the fast pipeline's polling frequency.

### Acceptance criterion for release coverage

> **Every update listed on Web漫画アンテナ or 百合ナビ should appear in this feed over time, with the
> attesting source recorded.**

Historical completeness is explicitly **not** required. What ran before we started watching a
platform is imperfectly knowable, and that is accepted — see the bootstrap discussion below.
Forward coverage is the target. Adult-rated material remains subject to DEFINITIONS §7 regardless.

This makes both a **yardstick**, not a source. They stay Tier C and attest nothing; what they
provide is a measurable gap.

Two lists, differing in kind:

| | Works | Platforms | Character |
|---|---|---|---|
| [Web漫画アンテナ 百合 tag](https://webcomics.jp/tag/%E7%99%BE%E5%90%88) | ~1,530 | ~96 | Crowd-tagged, broad |
| [百合ナビ WEB連載中の百合漫画](https://yurinavi.com/2017/02/28/web_yuri/) | ~130 | ~19 | Hand-maintained, much narrower |

> **Neither is a precision filter.** The antenna is crowd-tagged. 百合ナビ's list is maintained by
> hand but its inclusion standards are traditionally loose — it dates from a period when far less
> yuri was published and posting about a work was cheap. Being listed by either says a work exists
> and where; it says nothing about content, and **neither may be cited toward `content_tier`**.
>
> An earlier version of `coverage_union.py` weighted the curated list 4× on the assumption that
> hand-curation implied higher precision. It does not. The weighting was removed rather than
> retuned.

百合ナビ's list URL carries a stale 2017 date. The page is current; WordPress permalinks are not
dates.

百合ナビ also runs a 発売日 calendar covering **volume** releases rather than web chapters. It is
parsed by `adapters/yurinavi/calendar.py` and written to `data/unwired/`, which is read by nothing
— not the build, not the site. Its distinguishing content is forthcoming releases, whose value is
unclear, so the parsing is kept rather than the feature built.

If it is ever wired up, two constraints apply. It is Tier C and attests nothing. And **a scheduled
date is a claim about the future, not an observation** — release dates slip, so it can never be
stored as a publication date under the rule above.

#### The metric is platform coverage, not per-work overlap

Measured 2026-08-01 across all 31 pages of its 百合 tag: **1,532 works on 96 platforms.**

A naive per-work comparison scores 0.6%, which is misleading. Atom feeds are a rolling window of
recent entries, so no snapshot of ours can match a full catalogue — but **every update on a watched
platform passes through its window eventually**, which is precisely what the criterion asks for. So
the gate is whether a platform is watched at all:

| | |
|---|---|
| Platforms watched | **9 of 96** |
| Listed works living on a watched platform | **661 of 1,532 (43.1%)** |

The long tail is real — 96 platforms — but weighted by works it concentrates hard. The largest
unwatched venues are ニコニコ漫画 (175), pixivコミック (130), サンデーうぇぶり (65), マガポケ (37)
and COMIC FUZ (34). Adding those five would take work coverage past 70%.

`adapters/webcomics/coverage.py` writes the full gap to `data/coverage/`, which is the work queue.

### Two identification modes, because most platforms label nothing

GigaViewer ships in two generations. The newer Next.js build renders genre chips on its series
listings; the classic server-rendered build carries title, author and tagline and **no genre data
at all**. Verified 2026-08-01: none of the classic hosts exposes a working `/tag/` or `/genre/`
page either.

This is DEFINITIONS §4's labelling bias in concrete form, so platforms onboard in one of two modes:

| Mode | How a release is identified | Platforms |
|---|---|---|
| `genre` | The platform's own genre or label marks the series yuri. Establishes `marketing_label`. | 一迅プラス |
| `known-works` | The work was identified as yuri **elsewhere**; the feed only attests that a release happened. | the other 8 |

A known-works match is **identification, not classification**. The work's `marketing_label` comes
from wherever it was established — the print catalogue, a labelling platform, a confirmed discovery
candidate — and the general platform contributes nothing to it. Records carry `identified_via` so
the two can never be confused.

#### The known-works set is currently the binding constraint

Onboarded 2026-08-01: nine platforms live, one disabled. The eight known-works platforms produced
**zero matches** against a known set of 386 titles, across 402 distinct works in their feeds.

That is a real result, not a broken matcher (verified by probing titles known to be in the set).
The known set is presently 百合姫コミックス print works plus 一迅プラス series, and those are not
serialised on 講談社's or 集英社's platforms. So the infrastructure is in place and idle: it starts
producing the moment the known set covers works published there, which is what confirming discovery
candidates does.

The alternative — trusting a general platform to tell us what is yuri — is the thing DEFINITIONS §4
says cannot work.

#### Health checks learned two corrections here

- **A 200 is not proof of a feed.** `mangacross.jp/atom` returns HTTP 200 while serving its React
  app shell; its `/tag/百合` likewise 200s while returning the homepage. The adapter now requires an
  Atom `<feed>` root before believing any of it, and mangacross is disabled with the reason recorded.
- **A small feed is not a broken feed.** The entry-count floor was 5, which failed comic-trail for
  returning 3 genuine entries. Only an *empty* feed indicates breakage; the floor is now 1.
- **One bad source degrades one platform.** A malformed feed previously killed the whole run.

### A series is often on several platforms, and they are not equivalent

19.6% of works on Web漫画アンテナ's 百合 tag appear on more than one platform, up to six each. Three
facts follow, each of which breaks a naive approach:

**Releases are not simultaneous.** The same chapter can land a day or two apart. Exact-timestamp
matching fails; no matching at all produces duplicates separated by a couple of days, which read as
two chapters. Releases merge on work + chapter number within a 3-day window, and the earliest
sighting sets the date, which is then locked as under the rule below.

**Platforms differ in reading quality.** Image resolution and free-chapter availability, including
where free but rate-limited (待てば無料 / チケット). Where a chapter is in several places the feed
points at the best one and names the alternatives. The ranking lives in `data/platforms.yaml` and
is **editorial curation, not a fact from any source** — it affects only where a reader is sent,
never inclusion or classification.

**A platform can silently stop carrying a series.** No notice, no end marker; chapters simply stop
appearing there while continuing elsewhere. So the preferred source is chosen **per release, from
the platforms that carry that release** — a platform being better in general is no use if it lacks
chapter 13. A platform trailing the leader by two or more chapters is marked `lapsed`, which is a
caution about following the series there and **never** evidence that the series ended.

`adapters/crossplatform.py` implements this and `adapters/test_crossplatform.py` pins it. The tests
were written before any multi-platform data existed — only 一迅プラス is producing releases so far —
so the behaviour is fixed by stated fact rather than by whatever the first sample happened to show.

#### Coverage is counted in works, not presences

Because of the overlap, a work is a gap only when it is on **no** watched platform. Counting
platform-presences overstates the gap and mis-ranks the targets:

| | Listed | Reachable nowhere watched |
|---|---|---|
| ニコニコ漫画 | 175 | **91** |
| サンデーうぇぶり | 65 | **65** |
| pixivコミック | 130 | **63** |
| COMIC FUZ | 34 | **34** |
| マガポケ | 37 | **14** |

Measured 2026-08-01: 1,532 listings are **1,203 distinct works**. Coverage moved through the
session as platforms were onboarded:

| Platforms watched | Works reachable |
|---|---|
| 9 | 645 (53.6%) |
| 11 (+サンデーうぇぶり, webアクション) | 730 (60.7%) |
| **12 (+COMIC FUZ)** | **764 (63.5%)** |

**The syndication prediction held.** Onboarding those three cut ニコニコ漫画's exclusive count from
91 to 76 and pixivコミック's from 63 to 55, without touching either. Their apparent coverage really
is largely other platforms' work seen through them, so neither is a coverage target — onboarding
origins erodes them for free.

#### Overlap is measured, and it re-ranks the targets again

Per-platform overlap — the share of a platform's works that also appear elsewhere — is measured in
`data/coverage/platform-overlap.yaml`:

| Platform | Works | Overlap |
|---|---|---|
| pixivコミック | 130 | **0.77** |
| マガポケ | 37 | 0.76 |
| ニコニコ漫画 | 173 | 0.71 |
| COMIC FUZ | 34 | 0.38 |
| カドコミ | 243 | 0.28 |
| ビッコミ | 25 | 0.04 |
| **サンデーうぇぶり** | 65 | **0.02** |
| 少年ジャンプ+ | 51 | 0.00 |

> **Overlap does not establish direction.** A high-overlap platform may be syndicating others' work
> or originating work that others syndicate; this data cannot tell them apart. What it measures is
> **unique contribution** — a high-overlap platform adds little unobtainable elsewhere, whichever
> way the syndication runs. That is what governs onboarding priority, so direction is left
> unasserted unless separately known.

Where direction *is* known it is recorded with its source. ニコニコ漫画 is largely but not solely a
syndicator (project owner, 2026-08-01), with notably worse image quality — so despite topping the
raw count it is a poor target and a poor `preferred` source.

This corrected a claim of mine: I had recorded pixivコミック as an origin platform on no evidence.
At 0.77 its overlap is *higher* than ニコニコ's, so its 63 currently-exclusive works are expected to
shrink as other platforms come online.

**サンデーうぇぶり is the clearest target**: 65 works, overlap 0.02, so its exclusivity is real and
will not evaporate. COMIC FUZ follows on quality and exclusivity, at higher technical cost.

### Platform dates are claims, not observations

**A platform's own timestamp is not evidence of when something was published.** Verified on
GigaViewer, 2026-08-01: the Atom feeds carry `<updated>` and **no `<published>` element at all**, so
the value is last-modified by definition. Sites mass-update it during metadata refreshes and when
importing an existing series, collapsing a whole run of chapters onto one instant.

The signature is measurable. Of 37 entries in one feed, 4 distinct timestamps; one of them carried
25 entries from only 3 works. A shared timestamp is unremarkable when it is a scheduled daily batch
— many works, roughly one entry each — and suspect when a single work contributes several entries
at an identical instant. Records crossing that threshold are flagged `date_confidence: low` with the
count that triggered it.

#### The rule

```
effective date = min(claimed date, first scrape date)   — fixed at first sight, never revised
```

A claimed date **earlier** than our first scrape is accepted: the release plainly existed before we
looked, so the platform's claim is the better evidence. A claimed date **later** than our first
scrape cannot be a publication date for something we had already seen, so our observation wins.

**The load-bearing half is the second clause.** If the platform later changes its claim — which
these platforms do, in bulk — the stored date does not move. Everything else in this section is
bookkeeping around that one rule.

`adapters/gigaviewer/test_dates.py` holds it as a regression test: claimed-earlier wins,
claimed-later loses, and a subsequent change in either direction leaves the stored date untouched.

#### A future date is a schedule, never a release

COMIC FUZ returns `updatedDate` on chapters that have not been published yet — 40 of 1,880 when
first read, every one of them `purchase`. They are scheduled unlock dates.

Two rules, both learned by shipping the bug: **future-dated entries never enter a release feed**,
and **a rolling window is anchored to today, not to the newest date in the data**. Anchoring on the
data pulled months of back-catalogue into the feed because the newest date was five months ahead.

This is the same rule as the 発売日 calendar's — a date the world has not yet produced is a claim,
not an observation — arriving from a source where it was not expected. Worth assuming any date
field may contain one.

#### Fields

Each release carries:

| Field | Meaning |
|---|---|
| `first_seen` | When **this database** first observed the release. Never revised. |
| `first_reported` | The platform's timestamp **as it stood when we first saw it**. Never revised. |
| `platform_updated` | The platform's timestamp now. May move. |
| `date` | Earliest of the above, fixed at first sight. What everything downstream uses. |
| `date_basis` | `bootstrap` or `observed` — see below |
| `platform_date_changed` | Recorded when `platform_updated` diverges from `first_reported` |

A later mass-update at the source is **recorded as divergence and not followed** — §4's
append-and-mark applied to timestamps.

#### It is mostly a first-import problem, and it decays

`date_basis` distinguishes the two cases, and the distinction is what makes the problem temporary:

- **`bootstrap`** — the release was already there when tracking of that platform began. Its date is
  inherited from the platform with nothing observed behind it. Every record from a platform's first
  run is bootstrap.
- **`observed`** — the release appeared between two runs. `first_seen` then genuinely bounds the
  true publication date from above, and no later rewrite can move it.

So the unreliability is concentrated at the start of tracking a platform and shrinks with every
subsequent run. The cost of adding a platform late is a block of bootstrap records; the cost of
never locking dates would be a database that silently rewrites its own history whenever a publisher
tidies its metadata.

The interface states which case a date falls under rather than presenting all dates alike.

### Observation is passive — never authenticate, never purchase

Access terms are read from **public listing metadata and the platform's own labelling**. The
crawler does not create accounts, does not log in, does not spend points or tickets, and does not
purchase. `free-account` is recorded because the platform says so, never because we tested it.

Besides being the correct posture toward these services, this keeps the pipeline clear of anything
resembling access-control circumvention, and means no credentials ever exist for the automation to
hold.

### Presentation

**Expired and unavailable releases are collapsed, not removed.** They stay in the record and stay
reachable — the default view groups them behind a summary that keeps the count visible
("17 expired chapters"), so the shape of a series' history is legible at a glance without the
current state being buried. Nothing here overrides §4: releases are never deleted.

### Archive capture — content is not archived

Releases expire fast, so archive capture at first sight matters more here than anywhere else. But
this collides with the media policy (§2) and the line must be explicit:

> **Archive the listing, never the content.** What is captured is evidence that the release
> happened — the series index or chapter list showing its title and date. Never the reader page,
> and never the pages of the work itself.

Capturing a chapter reader page would mirror the manga, which §2 forbids outright regardless of
who is doing the mirroring or why.

### Polling

Release tracking runs as a **separate pipeline on a faster cadence** than the bibliographic
refresh, scoped only to works that are ongoing and web-published — which is what keeps its cost
bounded. Sources are Tier B platform feeds (RSS/Atom and JSON endpoints where available, HTML
listings otherwise), subject to robots.txt, conditional requests (ETag / If-Modified-Since) and
per-host rate limits.

Cadence is set by access volatility rather than by publication schedule: a weekly serial needs
checking more often than weekly, because its free window closes on its own timetable. Conditional
requests keep the cost of that proportionate.

**Aggregators as fan-out reducers.** Web漫画アンテナ (§1) watches many platforms at once, so it can
act as an update *trigger* — poll one antenna cheaply, then confirm on the platform only where
something moved, instead of polling twenty platforms on a fixed schedule.

Two limits on that, both following from §1's role separation:

- The antenna signals that something changed. **The platform remains the attesting source** for
  what the release is.
- **Access terms never come from an aggregator.** `access_modes` are read from the platform's own
  labelling, because free/待てば無料/purchase status is precisely what a third-party listing gets
  wrong or omits.

An antenna is also a poor tripwire for *disappearance*: it reports what appeared, not what left.
Expiry and delisting still require looking at the platform.

Print serialisation is *not* covered by this section. Its chapter-level data comes from MADB's
magazine and serialisation datasets at a different granularity and cadence.

### Scale consequence

A long-running serial accumulates hundreds of releases; across the corpus this is the largest table
in the database by a wide margin. Releases are therefore compiled into **per-work shards loaded on
demand**, never into the main search index — otherwise the static site's initial payload grows with
total release history rather than with the number of works.

---

## 6. Architecture

### Layered records

```
  source layer     one file per (work × source), stored as fetched, never hand-edited,
                   append-and-mark only — entries are withdrawn, never deleted (§4)
       ↓
  release layer    per-work release logs for ongoing web manga (§5), same append-and-mark rule,
                   written by the fast pipeline only
       ↓
  overlay layer    human curation and classification, with basis; never overwritten by bots
       ↓
  build            merge by source priority → validate → compile
       ↓
  publish          sharded JSON + prebuilt search index → GitHub Pages
                   releases in per-work shards, loaded on demand
```

Records are **YAML in git**: diffable, reviewable in PRs, and legible without tooling. The
separation of source from overlay is what satisfies openBD's no-modification term and what keeps
automated refreshes from ever clobbering curation. The source layer's git history is the project's
deepest archive (§4).

### Source adapters and format drift

Several rules in this document are necessarily loose — inferring `access_modes` from a platform's
labelling, recognising 公開終了, typing a release, telling a correction from a withdrawal. The
architecture must not turn that looseness into unreliability at runtime.

The governing split:

> **Steady state is deterministic and contains no judgment. Judgment happens out-of-band, when a
> human asks Claude to perform maintenance, and lands in the repository as data.**

**In-repo runtime (the cron) is a pure function.** Fetch → apply adapter → normalise → diff. No
model calls, no heuristics, no API keys in Actions, fully replayable from a fixture. Given an
unchanged site format it produces identical output every run, and it keeps working indefinitely
without anyone touching it.

**Out-of-repo maintenance is Claude-driven and periodic.** When an adapter reports degradation, or
on a routine cadence, a human directs Claude to inspect the changed source, update the adapter and
its fixtures, and open a PR. Format drift is a maintenance event, not a runtime problem to solve
automatically. Nothing self-heals.

#### Adapters are declarative data, not code

One versioned spec per source or platform: selectors, patterns, field mappings, label lookup
tables, and health assertions. Because an adapter is a small data file rather than logic scattered
through a scraper, updating one is a bounded, reviewable edit — which is precisely what makes the
out-of-band maintenance loop practical.

Each adapter carries a `last_verified` date, so staleness is visible rather than assumed.

#### Health assertions — fail loudly, never quietly

Every adapter declares invariants: minimum expected yield, the proportion of records that must
parse a date, the set of labels considered known. On violation the adapter is marked `degraded`,
**stops writing for that source entirely**, and raises an alert.

This interlock matters more than it looks. Without it, a site redesign makes a scraper return
nothing — and under §4 and §5 an empty result would be read as everything having been withdrawn or
expired at once. Append-and-mark means that is not data *loss*, but it is a mass false statement,
which is nearly as bad. So the rule is explicit:

> **A failed or degraded fetch means "we could not look", never "it is gone."** `last_confirmed` is
> left untouched and no withdrawal, expiry or availability change is recorded.

#### Unknown values are quarantined, never coerced

When an adapter meets a label it does not recognise, it records the value as `unknown` **together
with the raw observed string**, and does not guess. Those raw strings are the evidence Claude uses
to extend the mapping at the next maintenance pass.

This is how the loose rules become reliable: the fuzzy step is a lookup table maintained by Claude
out-of-band, and anything the table does not cover is preserved verbatim for later rather than
forced into the nearest enum value.

| Loosely specified rule | Runtime behaviour | Maintenance |
|---|---|---|
| `access_modes` from platform labels (§5) | Per-adapter lookup table; unmatched → `unknown` + raw string | Claude extends the table |
| `expired` / 公開終了 detection (§5) | Declared marker patterns; unmatched → **no state change** | Claude extends patterns |
| `release_type` (§5) | Keyword table; unmatched → `unclassified`, never guessed | Claude reviews the backlog |
| Correction vs withdrawal (§4) | Never decided at runtime — flagged in the PR | Human or Claude review |
| `content_tier`, `marketing_label` (DEFINITIONS §3–4) | Never automated at all | Human or Claude, with `basis` |
| Pornography signals (DEFINITIONS §7) | Explicit marker match only; ambiguous → **withheld** | Human review before publication |

Note the asymmetry in the last row. Everywhere else the safe default is to **preserve and not
assert** — keep the record, change nothing, flag it. For the pornography filter alone the safe
default inverts to **withhold**: an ambiguous case is not published until a human has looked at it.

#### Fixtures

Each adapter ships captured samples so that drift is caught by tests and so Claude can verify a fix
without hitting the live site. Fixtures are **structurally reduced** — the markup skeleton and the
specific labels and dates under test, with prose elided. A raw page capture would embed publisher
synopsis text and breach §2.

### Validation — build fails on any of these

- a field whose `source` is not on the allowlist (§1), excluding the `title_en_official` carve-out
- a `content_tier` or `marketing_label` without a `basis`
- a missing `first_publication` (venue, date, country) — it is the inclusion test
- **a work record deleted rather than marked withdrawn** — see §4; the build compares against the
  previous commit and rejects any disappearance not accompanied by a takedown record
- an attested field missing `first_seen` / `last_confirmed`, or in a `withdrawn-at-source` state
  without a `withdrawn_at` date
- a web-manga record without an archive URL captured at first sight
- **a release removed rather than moved to `expired` or `unavailable`** (§5) — same rule as works
- a release without a `release_type`, or an archive URL pointing at a reader page rather than a
  listing (§5)
- an `available` release with `access_modes` set but no `access_observed_at` (§5)
- a record written by an adapter in a `degraded` state, or a withdrawal/expiry recorded during a
  degraded or failed fetch — "we could not look" is never "it is gone"
- an `unknown` value stored without the raw observed string that produced it
- any release carrying `access_modes` while `availability` is `expired` or `unavailable` — access
  terms describe reachable releases only
- a work matching any pornography signal (DEFINITIONS §7) that still holds a record
- a cover reference on an `explicit_content: true` record
- a cover reference whose origin is not a publisher-supplied reuse feed
- stored text matching a known publisher synopsis

Deletion is possible only through an explicit, human-authored takedown record naming the requester
and date. There is no other path by which a work or a release leaves this database.

### Self-updating

GitHub Actions on a cron: fetch → normalise → diff → **open a pull request**. Never a direct
commit to the main branch. The diff is the review surface; a bot that silently rewrites records is
a bot that silently corrupts them.

The automation has **no capability to delete a work or release record** — not as policy but as a
matter of what the code can do. Its available operations are add, supersede-with-evidence,
mark-withdrawn (§4) and mark-expired/unavailable (§5). Where it cannot tell correction from
withdrawal, it opens the PR with the ambiguity flagged for a human.

The two pipelines run on different cadences (§5) and write to different layers, but both are bound
by these rules. The release pipeline's higher frequency makes PR-per-run impractical; it batches
into a periodic PR, with new works or ambiguous states escalated immediately.

### Web-manga volatility

Japanese platforms routinely delete works when serialisation ends or moves behind payment — and
unlike print, a delisted web work may leave no trace anywhere else. These are the records most
dependent on §4 and the ones most likely to make this database the last remaining evidence that a
work existed.

Web records therefore carry `first_seen` / `last_confirmed` and an **archive URL captured at first
sight**. On delisting they move to `withdrawn-at-source` and remain fully visible, rather than
becoming an unverifiable claim or vanishing with the platform.

### Interface

Static site, client-side search, no server. Stored strings are Japanese (原題 + よみがな/romaji
transliteration — transliteration is not a foreign source and does not breach the firewall), plus
`title_en_official` where it exists. Interface chrome and classification labels are bilingual.

Default view: the inclusion test of DEFINITIONS §2, with `incidental`-only works hidden and the
classification boundary adjustable by the reader.

Three things are collapsed rather than hidden, each expandable and each keeping its count visible:
`incidental`-only works, releases that are `expired` or `unavailable` (§5), and fields in a
`withdrawn-at-source` state (§4). The site never presents a smaller history than it holds.

Access terms (§5) are a first-class filter — "readable now for free", "free with an account",
"free if you wait" — and are always rendered with their observation date, degrading to a
last-seen statement once stale rather than asserting terms that may have lapsed.

---

## 7. Phasing

**Phase 1 — 百合姫 lineage, end to end.** The full pipeline against a bounded, high-signal corpus:
『百合姉妹』→『コミック百合姫』(and offshoots) →『つぼみ』→『ガレット』. Schema, the adapter
framework (§6) with two or three real adapters, validation, build, and a working Pages site. Every
layer proven against roughly 500–1,000 works before scaling.

> **Corrected 2026-08-01.** This originally pointed at MADB's magazine-serialisation datasets. Those
> hold no contents records for any yuri magazine. The corpus comes instead from the 単行本 imprint
> field (`schema:brand`): 646 volumes, 302 works, 2006–2026, all with ISBNs. Publisher sources are
> still needed for the three magazines MADB lacks and for serialisation detail. See [MADB.md](MADB.md).

The adapter framework is Phase 1 work rather than a later refinement: it is the mechanism that
decides whether this project needs continuous attention or periodic maintenance, and that is the
difference between it surviving and not.

**Phase 2 — historical spine.** MADB + NDL sweep for pre-2000 print, the coverage no existing
database has.

> **Reassessed 2026-08-01.** This was framed as the harder, later problem. MADB's contents data is
> concentrated on 花とゆめ (849 issues), なかよし (806), りぼん (776) and 月刊漫画ガロ (412), which
> are the magazines where Class S and the pre-1990s precursors ran. This phase may be the *more*
> tractable one from bulk data. Whether to reorder is open.

**Phase 3 — breadth.** Current print and web across all publishers, and the release-tracking
pipeline (§5) extended across all ongoing web serialisations. Release tracking is prototyped
earlier, in Phase 1, against whichever 百合姫-line titles run online — the mechanism needs proving
on a handful of platforms before it is pointed at many.

**Phase 4 — doujinshi.** Subject to the R-18 reality described in DEFINITIONS §7, and to a
decision made at that point rather than now.

---

## Verification status

Verified live on 2026-08-01: openBD terms and cover-reuse permission; MADB dataset availability,
formats, manga coverage, licence terms, and the `bunka.go.jp` → `artmuseums.go.jp` migration.

Also verified 2026-08-01: 百合ナビ (release calendar and news blog) and Web漫画アンテナ (百合 tag,
~900+ works across 31 pages, cross-platform with links back to source) as Tier C; COMIC OGYAAA!!,
ComicWalker 百合倶楽部 and BOOK☆WALKER's 百合 tag as Tier B candidates.

Still to verify: NDL Search API surface and query semantics; Books.or.jp access; whether 百合ナビ or
Web漫画アンテナ expose feeds or only HTML; the current MADB dataset release; and the exact
composition of the magazine lineage in DEFINITIONS' appendix.

Nothing in this document is legal advice.
