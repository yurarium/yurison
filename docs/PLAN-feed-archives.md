# The updates feed, its archives, and when we learned a thing

Outlined by the project owner as B4, planned 2026-08-11. Progress is marked here.

What an archived month is for: **what changed then**. New works, new chapters, one-shots, access
changes. What we called a work or an author at the time is not history; a name has a right answer
we converge on, and an archive showing a name nobody uses is simply wrong.

## 1. `feed_date` for a web release comes from the first-seen ledger

`_fdate` files a row by `feed_date` and falls back to `pub`, so a chapter published in July and
first seen in August belongs to AUGUST, drawn as `既出 07-31` with the day it was published. That is
the mechanism for showing old news without rewriting the month it was published in, and it is right.

**It is applied in one adapter and the ledger it needs is complete.** `late_discovered` is set by
the generic webpage route alone, when the update is older than `WEBPAGE_FEED_DAYS`. Every other
route leaves it unset and lets `feed_date` fall back to `pub`. Measured 2026-08-11 by building the
same commit in a fresh clone: 119 rows landed in July that the published July never had, **all 119
web releases, all 119 already in `data/ledger/first-seen.yaml`**, with first-seen dates of 7 and 10
August against publication dates of 30 and 31 July. `スローループ 第76話` is the example: the ledger
knows we first saw it on 2026-08-07 and the row went into July with `late_discovered` unset.

So the rule moves to where the feed is assembled and reads the ledger, on every route.

**WEB RELEASES ONLY.** A printed volume is dated by its publication and a catalogue reaching us late
says nothing about when the book came out. The ledger is keyed `work|episode|platform` and holds
web chapters, which is the population this applies to.

**AN EARLY GLUT IS ACCEPTED.** The ledger starts when tracking started, so a stretch of rows will
carry the marker at once. The owner ruled on 2026-08-11 that the marker is used consistently even
so: a truthful glut beats a rule applied where it happens to be convenient.

## 2. Archives carry no rendering

602 of 605 rows in `2026-07.json` bake `work_en` and `author_en`: the reading, the ruby and all
three romaji styles, written once. **573 of them now show a title the store no longer holds** and
116 a stale byline. `球詠` reads `Tamaei` where the store holds `Tamayomi`; `友達からでもいいですか`
reads `Tomodachi Karade mo Iidesu Ka` where it is now `Can We Start as Friends?`.

`docs/FEATURES-INTERFACE.md` already states the design: *"Names are joined onto archived rows at
render time from `feed/names.json` rather than by rewriting them. A romanisation improving is the
system working; a published date changing is not."* The code does not do it. Dropping the two
fields takes the file from 803 KB to 540 KB, and the 33% removed is the third of the archive that
was wrong.

`work` and `author` stay. They are the key the renderer resolves against rather than a rendering.

## 3. Archives stay derived, and stay out of the repository. CONFIRMED

With 1 in place, a month is a function of `data/source` and the committed ledger, so a fresh
checkout reproduces what was published. Nothing needs committing.

This reverses what this session was about to recommend. The archive was going to be committed
BECAUSE it could not be reproduced, and it could not be reproduced because a rule was applied in
one adapter instead of at the feed. Committing it would have frozen 602 stale renderings into the
repository and called them a record.

## What this unblocks

`gate.yml` now runs on `main` and is red, because CI measures a corpus no reader has: a fresh
checkout derives 681 rows for July against the published 605, and four budgets differ as a result.
That is this fault, seen from the gate. See [PLAN-credits-and-gates](PLAN-credits-and-gates.md).

## What is settled and needs no further decision

**The line is drawn around July's ROW SET and around nothing else.** The month was largely
retconned and the owner has accepted it as the basis it formed on, so which updates sit in July is
settled: item 1 changes which month a row is filed in from now on, and the 119 move to August
rather than July gaining them.

**July renders live, like every other month.** Accepting the row set says nothing about how those
rows are drawn, and a name has a right answer whatever month it appears in. So item 2 applies to
July as much as to any month after it, and the 573 stale titles in it are in scope.

## The late-discovery badge said the one thing that cannot be true. Fixed 2026-08-11

The updates tab drew `既出` with the publication date beside it and glossed 既出 as `Seen`, so a
chapter published on 17 June and found today announced itself as `Seen 06-17` on the day it first
appeared. The releases tab draws the same fact as `公開 2026-06-17` with the tooltip "published
earlier; it reached this list on 2026-08-11", which is right and always was.

Two renderings of one fact, worded independently, and the one nobody was reading drifted into
saying something false. It only became visible when item 1 started producing these rows: the badge
had been unreachable while `BOOTSTRAP` suppressed every late discovery. Glossed `Published` now.
Worth folding the two into one renderer, which is not done here.

## Open

Whether `basis`, `conf` and `unverified` on an archived row are history or rendering. They are
claims about the evidence at that time, which reads like history, and they attach to the name,
which reads like rendering. Not settled here because nothing turns on it until item 2 is written.

## Progress

1. `feed_date` from the ledger, every route, web only. DONE 2026-08-11

`BOOTSTRAP = True` forced `feed_date = pub` on every row, so the marker was computed, stored and
never acted on. It is a date now: a sighting ON 2026-08-02, the day the ledger was seeded, is not
evidence and the row keeps its publication date; a sighting after it is one the pipeline witnessed
and the rule applies. The exception expires as the seeded rows age out.

Lateness is measured in MONTHS, because the archive's unit is the month. A day rule left 54 rows
homeless: published 31 July, first seen 7 August, inside the 14-day window so not late, and July
closed on 1 August and never reopens. A fresh checkout derived July as 681 rows under the old
behaviour, 659 under a day rule and 606 under this one, against a published 605.

109 rows moved from the archive into the current feed and carry the marker, which is the glut the
owner accepted. Four budgets rose with them, all because the current feed now has more rows to
measure.
2. Archives carry no rendering. DONE 2026-08-11, by re-deriving rather than by dropping fields

The plan was to drop `work_en` and `author_en`. That was too small: `work` and `ep` are frozen too
and are equally subject to naming fixes, so July held titles this session had already corrected.
`archives are unchanged` was the thing preventing an archive from ever tracking current data.

The owner amended it. An archive locks its ROW SET and not its bytes, the file is rewritten every
build, and `no published update leaves its month` asks whether an update we published stopped being
published, keyed on the platform's own id because the title is exactly what may change. July's 573
stale titles are 0, and the truncated and reversed titles went with them.

Item 1 is what makes this safe: a row's month comes from the ledger, so re-deriving cannot move one.

Section 3 asks for no work. It is written down so that committing the archives is not done by
mistake, which is what this session was an hour away from doing.
