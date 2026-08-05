# Interface plan: the work as the unit

What the site becomes once the print and retailer captures land. A plan, not a record of decisions.
[FEATURES-INTERFACE.md](FEATURES-INTERFACE.md) holds what is built; anything here moves there as it
ships, and anything abandoned is deleted rather than left standing.

Layer 3 of the authority order. It may not contradict [Requirements](REQUIREMENTS.md) or
[Definitions](DEFINITIONS.md), and §1 of FEATURES-INTERFACE governs throughout: the interface
states facts about manga, and facts about us go to `status.html`.

---

## 1. What is actually changing

The database holds two populations that are joined on nothing, and the interface exposes that split
as a tab. `series.json` carries 993 web serialisations where every field is chapter-shaped, and
`index.json` carries 302 print works where every field is book-shaped. They overlap on 70 works,
and a reader meets `やがて君になる` as a chapter feed under 作品 and as a volume run under 単行本
with nothing saying they are the same story.

The retailer captures make that untenable rather than merely untidy. `data/queue/` now holds 4,303
candidate rows from two shops, matching 288 and 175 of our works respectively, and almost all of
what they add is print volumes of works we have no serialisation route to.

**The work becomes the unit.** A serialisation and a book run are two publications of one work, and
the interface should say so. 単行本 stops being a population with a tab and becomes a property of a
work, which is what dissolves the split rather than papering over it.

## 2. Identity, and the join as a claim

A web work has no identifier. `series.json` rows are keyed on the title string, which is the thing
this project spent 2026-08-04 correcting, and `index.json` rows carry MADB C-numbers that 923 of
the 993 web works have no equivalent for. Every join measured so far, including the ones in this
plan, is a folded title key. That is adequate for counting an overlap and inadequate for a
permanent link.

**Mint an internal identifier and hang the external ones off it.** The record becomes an authority
record: our id, plus the MADB C-number, the NDL record, the shop series and title ids the captures
already collect, and each platform URL. Those are better join keys than a title because a shop's
series page also states the imprint and the author, so agreement can be checked rather than assumed.

**The join is a claim and carries a basis (§5).** Asserting that a serialisation and a book run are
one work is the same kind of statement as asserting that a work finished, and it can be wrong in
the same way: `citrus+` returned an unrelated 2007 book from NDL on a title match alone. Record why
two publications were linked.

A minted id also survives title correction, and this project corrects titles often. Several were
corrected on 2026-08-04 alone, some from Latin forms read off splash art the same afternoon.

## 3. Three views

| view | holds | job |
|---|---|---|
| 更新 / Web Updates | chapter releases, newest first | get the reader to the chapter |
| 発売 / Releases | book releases, forthcoming and recent | tell the reader what is coming |
| 作品 / Works | one row per work, print and web alike | look something up |

The old 単行本 tab's contents move into Works, and Releases takes the slot with a different job.

**Web Updates and Releases are not one view with a mode.** Chapter releases run between 105 and 215
a week and averaged about 120 over the fourteen weeks to 2026-08-04. Print output is nothing like
that: 646 volumes across 302 works spanning twenty years, and even at six times the corpus, yuri
tankobon appear at something like eight a week. Merged and sorted by date, a volume would be one
row in twenty.

They also run in opposite directions in time. A chapter appears and then we hear about it. A
tankobon carries an announced 発売日 weeks ahead, so the rows worth reading are the ones that have
not happened yet. One view cannot default to both.

Layout follows from that, and it is the part a mode toggle could never deliver. **A release calendar
may carry cover images and a chapter feed may not.** REQUIREMENTS permits exactly one cover host,
`cover.openbd.jp`, because it is a publisher-supplied reuse feed, and `build.py` already refuses a
cover on an `explicit_content` record. We hold 252 openbd records carrying `cover_url` and exactly
one cover reaches the build today.

**The risk of a third view is that it re-forks the database into a web half and a print half**,
which is the state this plan exists to end. What keeps it honest is that both feeds link into the
same work pages. A tankobon in Releases and a chapter in Web Updates land on the same page for the
same work, and if they ever do not, the split has gone wrong.

## 4. The detail layer

A row cannot carry evidence, so today the evidence is invisible and a reader gets bare assertions.
A work page is where §5 finally has somewhere to live: what the work is, which publications carry
it, who published it under what imprint, and what says it finished.

**Evidence is not uncertainty.** "Four volumes from 幻冬舎コミックス, 2017 to 2020, and the shop
marks the series finished" is a statement about the world and belongs on the page. "We are not sure
whether this counts as yuri" is a statement about us and belongs on `status.html`. §1 of
FEATURES-INTERFACE is not relaxed by giving works a page of their own.

**Author pages fall out nearly free and are the biggest thing with no surface at all.** Roughly 640
pen-name readings were researched in the sessions to 2026-08-04, five names were refuted as another
person or not a person, and the two captures added several hundred more with their bases recorded.
None of it is visible anywhere except as furigana over a name in a row, and the claim behind it
cannot be checked at all.

Imprint and magazine pages are the same shape and are not in this pass. The lineage appendix in
DEFINITIONS is already a list of magazines with MADB ids, and 百合姫コミックス will be the largest
imprint in the print corpus, so they will want to exist later.

`status.html` is unchanged and is not a fourth view.

## 5. URLs and how the page stays fast

The single page and its responsiveness are kept. The data is small and carries no media, so the
whole corpus stays client-side and moving between works costs no fetch.

**Real paths, not fragments.** `history.pushState` to `/work/<id>/`, continuing what
FEATURES-INTERFACE already describes: navigation goes in the URL and preference does not, and the
address describes only what is visible. A fragment never reaches the server, so it cannot be
pre-rendered, and a citation that resolves only when JavaScript runs is a weaker promise than a
bibliographic database should make.

**Pre-render an entry stub per work, for cold entry only.** Two or three kilobytes carrying that
work's facts as real HTML plus a link to the shared bundle. Someone following a citation gets
content without JavaScript, and the script then boots and takes over, after which they are in the
same page as everyone else. At 3,000 works that is about 9MB of static files.

Indexing is **not** a reason for this. The page carries `noindex,nofollow,noarchive,nosnippet` and
that posture stands. The reasons are that a citation should survive a reader with no JavaScript,
and that a stable address for a work is most of what makes a reference work citable.

**The payload has to split, and this is the point at which it becomes necessary anyway.** A finder
row costs about 790 bytes, so the list index is 0.78MB now and about 2.4MB at 3,000 works. Full
detail is a separate matter: `series.json` carries chapter counts and not chapter lists, so a work
page showing chapters needs data we do not publish at all, and オトメの帝国 alone has 432. Detail
becomes per-work and lazy, which a per-work URL makes natural, and the initial load then shrinks as
the corpus grows.

None of that works until the bundle is split. `kari/index.html` inlines everything at 163KB, and
every stub would inherit that weight unless the CSS and script move to shared cacheable files.
This is the only real refactoring in the plan, and it makes repeat visits faster as a side effect.

**Pre-rendered pages outlive their works, and the deploy has to prune them.** プリンセ「ス」 left
the corpus and returned on the same day, 2026-08-04. A stale page for a work that no longer exists
is a zombie URL asserting something we withdrew, so `deployed data matches built` should cover
pages that exist for works that do not. It is the inverse of the carry-over rule and this project
will otherwise notice it only after shipping one.

## 6. Where a click goes

**In Web Updates the main link stays on the work and goes to the live work**, on the platform. That
is the high-frequency action and the reason the view exists. §7 of DEFINITIONS settled the outbound
question on 2026-08-03: linking to the work is fine, including to a reading page, because every
platform here is a commercial publisher's own web arm.

A subsidiary link reaches our page. The metadata line the row already carries, the author and the
chapter count, is the natural carrier, since it is the part of the row already about the work
instead of about the update.

**In Works the main link is our record**, because a reader there is looking something up.

**Consistency lives in the marking, not in the position.** Anything leaving the site carries the
same quiet marker in every view, so a reader learns it once and it never lies, and the primary link
is free to differ where the views' purposes differ. Forcing one rule across both would make one
view worse to buy a symmetry nobody experiences.

**A work on several platforms has several live destinations.** The feed already carries
`is_preferred`, so the compact link follows the preferred source and the work page lists them all.
`ハロー、メランコリック！` sits on three.

**Releases inverts it.** A chapter has a "read it now" destination and a tankobon does not; its
equivalent is a shop. Pointing a primary link at a retailer makes the view commercial in a way
Updates is not, particularly now that two shops are read for classification. The volume links to
our work page, and the work page carries the outbound links, including the publisher's own book
page and the shops we hold ids for.

A work page is a destination, so its links are explicit and labelled and there is no ambiguous
primary click to get wrong.

## 7. Scope, and what the default view holds

Both captures put roughly a third of their shelves in scope under DEFINITIONS §3. The deductions
are consistent: derivative fan work at 172 東方 items on BOOK☆WALKER, anthologies at 101 and 116
where the label attaches to the container and not to each contributor's story, editions and splits
inflating cmoa by around 250 rows with 推しが武道館いってくれたら死ぬ appearing three times, and
named cases like a 32-volume seinen action series that are plainly `incidental`.

§2 already has the lever, since works qualifying only as `incidental` with no label are recorded
and kept out of default views. The catch is that `content_tier` is empty on every print row, and a
retailer shelf is evidence toward that axis instead of a value for it.

**A reader-facing filter describes the work, not our confidence in it.** "In print" and "serialised
online" are properties of the work and are honest. Anything shaped like "well attested" puts system
uncertainty in the reader interface, which §1 forbids.

## 8. Order of work

1. Identity and the join, since nothing else can be built on a title string.
2. The bundle split, which blocks the stubs.
3. Works absorbing the print population, and work pages.
4. Author pages.
5. Releases, last, because it cannot be built from what we hold.

Everything captured so far is retrospective. Releases would launch as a list of things that already
happened, which is the opposite of its purpose. It needs a forthcoming-release route, and
`bw_new_schedule.xml` in BOOK☆WALKER's sitemap index is the obvious candidate, with openbd for the
ISBN, the date and the cover. REQUIREMENTS §5 already carries the discipline, since a future date
is a schedule and never a release.

## 9. Not settled

- **Settled 2026-08-04, and built.** The id is opaque: `w` and a zero-padded sequence, minted in
  `adapters/identity.py` and stored in `data/identity/works.yaml`. A readable stem would break on
  the title corrections this exists to survive. 1,223 works are assigned and 70 are joined across
  both populations. A work is looked up only by the anchor that identifies it, never by an attached
  one, because the corpus contains a MADB record whose title matches both a serialisation and its
  読み切り版, and lookup by any anchor silently made those one work. That contest is reported and
  sits in `data/queue/identity-review.yaml` for a decision.
- How an anthology is modelled. It is one publication with many contributors, and neither a work
  row nor an author page is currently shaped for it. 217 rows across the two captures are affected.
- Whether a doujin publisher can be identified reliably enough to filter on. Neither shop's own
  metadata does it: BOOK☆WALKER's facet misses 百合コレ, its largest doujin imprint at 516 rows, and
  cmoa's publisher field leaves seven indie distributors unestablished.
- 大洋図書 and キルタイムコミュニケーション are adult-adjacent commercial publishers whose stock is
  filed as ordinary 青年マンガ. They need a per-publisher decision that cannot be made from a
  listing row.

## 10. One bar, three tabs (2026-08-05)

The three tabs had grown three interfaces over the same idea. Updates carried a period, a search
box, three filters and a layout select; Works carried a search box and four selects; Releases
carried no controls at all, over 640 volumes. They now share one shape:

```
[ search .......................... ] [ 絞り込み ▾ ]
( the filters, collapsed by default )
[ period ▾ ] [ filter ✕ ] [ filter ✕ ]   条件を消す
count ................................ [ sort ▾ ] [ 簡易 | 詳細 ]
```

**Filtering happens above the line, arranging happens on it.** 簡易/詳細 spent its life in the
filter row looking like a filter. It formats output, so it sits with the output, opposite the
count, and Works' sort select joins it there.

**The chips exist because the panel is collapsed.** These preferences persist in localStorage, so
without them a reader returns days later to a narrowed list with nothing on screen saying so. A
collapsed panel may hide a control; it must not hide a fact.

**The period is a chip that cannot be removed**, because a period always has a value. It opens a
menu where the others carry a cross, and the chevron is what says which kind of chip it is. Works
has no period: there is no scope to state, so its chip row starts empty.

**Density is one preference, not three.** The three segmented controls are faces on a single
hidden `<select>`, the same arrangement the month picker uses. Compact is CSS dropping what a
reader scanning for a title does not read, so switching costs no render.

Releases gained search, a publisher filter and a period, and opens on the last twelve months
because the tab answers "what has just come out". The full 640 is one menu entry away and the
count line says which of the two is on screen.
