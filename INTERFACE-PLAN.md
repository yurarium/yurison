# Interface work — plan

Four topics. Two are pure interface; two need `build.py` to emit something it does not emit yet.
That split decides the order more than anything else.

---

## 1. A series/works tab for currently-reachable web manga

**Not buildable from `feed.json` as it stands, and the reason matters.** The feed is a 60-day
window — it currently spans 2026-05-25 to 2026-08-02. A series that last updated 61 days ago is not
in it. So a series tab built from the feed would answer "which series updated recently", while the
question asked is "which series can I read right now". Those differ by exactly the works most worth
listing: the long-running ones between arcs.

The data exists. `data/source/` holds 19,031 chapters across 1,453 work-records — full histories,
not windows. `build.py` throws that away when it windows the feed.

So: **new build output, `data/build/series.json`**, one row per (work, platform):

```
work, platform, url, author, chapter_count, first_chapter, latest_chapter,
latest_date, access of the newest chapter, free_chapter_count, also_on[]
```

Design questions to settle before writing it:

- **What does "currently reachable" mean?** A URL that resolves is not the same as a series still
  running. Proposal: three states — *running* (updated within ~90 days), *quiet* (older, but the
  chapter list is still served), *withdrawn* (the platform serves an empty list, which we already
  detect). Never guess "completed"; no platform reliably says so.
- **Row identity is (work, platform), not work.** 40 works are on more than one platform, and they
  differ in access and in how much is free. Collapsing them hides the thing a reader is choosing
  between. Compare 単行本, which is per-work because a volume is.
- The 単行本 tab is print. This tab is web. They should not share a sort or a filter set.

## 2. User-focused design for the detailed updates view

Pure interface, no build dependency. Start here.

The current detail row for one release:

```
吸血少女とウンディーネ  [既出 — 公開 2026-05-14] [読切] [読み切り]
【読切】吸血少女とウンディーネ  漫画：ふえふき  ·コミック アース・スター  [要分類]
初確認 2026-08-01
```

What is wrong with it, in the order it hurts:

1. **Work-product markers are showing.** `要分類` means *we* have not classified it yet. `初確認`
   is when *our pipeline* first saw it. Neither is a fact about the manga. This is the same fault
   as the preamble that was cut earlier — the view is showing the reader our bookkeeping.
2. **The chapter line repeats the work title.** 【読切】吸血少女とウンディーネ under
   吸血少女とウンディーネ. Common on one-shots, where the platform names the episode after the work.
3. **The kind is stated twice** — `読切` and `読み切り` are the same fact in two tags.
4. **The author field is unfiltered credit text.**
   `原作／宮澤伊織(早川書房刊)　作画／水野英多　キャラクター原案／shirakaba` is longer than everything
   else in the row and buries the chapter.
5. **No hierarchy.** Work, chapter, author and platform are all near-equal weight, so the eye has
   nowhere to land.

The row should answer a reader's four questions in this order: *what updated*, *is it free*,
*where do I read it*, *is this new to me*. Everything else is secondary or belongs in a details
disclosure.

## 3. Run breakdown and a change-over-time graph

Linked at the bottom, out of the way. Two halves with different readiness:

**The breakdown needs a run record that does not exist yet.** `build.py` prints its counts to
stdout and keeps none of them. Add `data/build/run.json` — timestamp, per-adapter rows written,
adapters that failed or returned nothing, validation results, the field-audit count. Then the view
is trivial and the value is real: *what did last night's run actually do, and what broke*.

**The graph can be built now, from data already held.** Releases per week by `pub` date covers the
full 60-day window immediately, and `data/ledger/first-seen.yaml` grows a genuine
first-sighting series from here on. Do not fabricate history for runs that were never recorded —
the graph should start where the record starts and say so.

Keep it deliberately plain. This is an instrument panel, not a dashboard.

## 4. Cap the updates tab and file past updates by date

`feed.json` is 1.3 MB for 1,387 rows (~964 B/row) and every visitor downloads all of it to see the
first screen. At a year of accumulation that is unreadable and unloadable.

Proposal:

- **Updates tab shows a bounded recent window** — 14 days by default, or the last N. Enough that
  the common visit ("what is new") never pages.
- **Archive by month**: `data/feed/2026-07.json` and so on, written by `build.py`, loaded on
  demand. A `/updates/2026-07` style view, linked from the bottom of the tab.
- The current file becomes `data/feed/current.json` and stays small.

Interaction with §5 date locking: archived months must be written **once and not rewritten**, or
a later run could revise a date the rule says is locked. The first-seen ledger is what makes it
safe to detect that.

Interaction with topic 1: the series tab is what makes a short updates window acceptable. If the
only way to find a series is to scroll the updates feed, the feed cannot be trimmed. Build 1
before 4.

---

## Order

1. **Topic 2** — pure interface, immediate, and it settles the visual language the other views
   will reuse.
2. **Topic 1** — the biggest gain for a reader, and it unblocks 4.
3. **Topic 4** — safe to trim the feed once series are findable elsewhere.
4. **Topic 3** — most valuable once the pipeline is running unattended, which it is not yet.
