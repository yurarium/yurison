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
