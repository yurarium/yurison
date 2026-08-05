# Interface features

What the reader-facing site does and why. Layer 3 of the authority order: it may not contradict
[Requirements](REQUIREMENTS.md) or [Definitions](DEFINITIONS.md), and the invariants in `check.py`
enforce the parts of it that admit a correct answer.

This is a **record of decisions**, not a plan. An earlier `INTERFACE-PLAN.md` covered four topics,
all of which are built and described here; that file is gone. The name now holds a new plan,
[INTERFACE-PLAN.md](INTERFACE-PLAN.md), for the interface once the print and retailer captures
land. Anything there moves here as it ships.

---

## 1. The governing rule

**The interface states facts about manga. Facts about us go to `status.html`.**

Coverage, confidence, what we have not reached, how we grouped something — none of it is
actionable by a reader, because no reader is going to check a listing site against a publisher.
Presenting it there is a category error, not a kindness.

The one deliberate exception is §5.

## 2. Three tabs

| tab | holds | source |
|---|---|---|
| 更新 / Updates | releases, newest first, grouped by day | `feed/current.json` + archives |
| 作品 / Works | one row per web work, its platforms listed as sources | `series.json` |
| 単行本 / Volumes | print works and their volumes | `index.json` |

**A work is one row with several sources, not several rows.** 雨夜の月 is one series that コミックDAYS
carries 121 chapters of and マガポケ 10 — that is two coverages of one story, not two lengths of it,
so the count is stated per source rather than summed or picked between.

## 3. The updates window

Fourteen days in `feed/current.json`; completed months in `feed/YYYY-MM.json`, fetched on demand.
Before this the tab downloaded 1.34 MB to render its first screen.

**An archived month holds the whole month**, overlapping the current window. The alternative — "the
month minus whatever the window still covers" — makes a file's contents depend on the day the build
ran, which breaks the write-once rule it exists to serve.

**Archives are written once and never rewritten** (REQUIREMENTS §5). A later run that would produce
different content warns, naming each differing row, and leaves the file alone. Names are joined onto
archived rows *at render time* from `feed/names.json` rather than by rewriting them — a romanisation
improving is the system working; a published date changing is not.

Only 2026-07 onward is archived. Earlier data was bootstrap-imported from platform back-catalogue
dates, and publishing it as "the updates of June" would assert a history nobody observed.

## 4. Language

Three modes: 日本語, EN, 併記.

**併記 renders the whole row twice, once per language, stacked.** Not an English title bolted under a
Japanese row — everything translatable is translated on its own line, so the English line is usable
without reference to the one above it. The second line is one step quieter so it reads as a
translation rather than a second entry.

**EN mode contains no Japanese at all** — no kanji, kana or full-width characters. Full-width
punctuation counts: ！？【】・～ read as Japanese typography however Latin the letters around them
are. Enforced by `inv_english_mode_has_no_japanese`.

Structure translates and content romanises: 第90話 becomes `Ch. 90`, 原作 becomes `story`, and the
name beside it is romanised. Doing either wholesale gives "Dai 90 Wa" and "Gensaku Miyazawa Iori",
which help nobody.

**Where nothing is held, the Japanese shows.** That is a finished state, not a gap.

**A date is mostly not a translation problem.** `08-03` and `2026-08-03` belong to neither
language: English would write 3 Aug and Japanese 8月3日, and the ISO order reads correctly to both.
It is also what the archive URLs and filenames use, so a reader who could switch it would see the
page disagree with its own links. Only two tokens are language-bound, the weekday and the month
name, and in 併記 both show: `08-03 月 Mon`.

The day heading is a divider, so it cannot take a second line the way a title does, but the token
is three characters and doubles along the axis that is free. Neither weekday
nor month name decided anything for 併記 before this: `LANG === 'en' ? EN : JA` gave it Japanese
because it is not `en`, so the page showed 月 beside a picker button reading 最新 / latest, from the
same mode, because that one happened to route through `T()`.

## 5. Marked and unmarked

Unmarked: an English name the work itself uses (`official-jp`) or a licensor publishes
(`licensed`).

Marked with a dotted underline: our romanisation or translation.

Marked `[?]`: a reading assembled character by character because no analyser could read the word.
Likelier wrong in a specific, visible place — the isolated reading of a character is often not its
reading in a compound.

**The unverified-reading mark is the one piece of our own uncertainty shown to readers, and that is
deliberate.** It is a fact about the content rather than about our process; a Japanese-literate
reader can judge it on sight, which was never true of 要確認; and it stops a real person being
authoritatively misnamed under their own work. Removing it would not simplify the interface, it
would move a cost onto someone who did not consent to it. See `NAMES-PLAN.md` §5d — **do not tidy it
away by applying §1 mechanically.**

## 6. Reader controls

Language, theme, romanisation style (ō / ou / o) and furigana. All persist in `localStorage`;
nothing is transmitted and no cookies are set.

**Controls that do not apply keep their space and go inert** rather than disappearing — a control
vanishing reflows the header and the reader loses their place. The always-applicable controls sit on
one row and the two language-dependent ones on a second, which is the fewest rows that lets them
come and go without moving anything.

Romanisation style is the reader's, not ours: all three forms are rendered at build time from the
same kana, so switching costs nothing and the store keeps no romanised string.

## 7. Badges

One size, one weight. **Colour is the only variable**, because it is the only difference that
carries meaning: accent = readable, grey = neutral, queue = ended, warn = costs something.

A badge states what the update did. `有料先行` is a standing fact about the series — how many
chapters sit ahead of the free line — and carries no count, because no number means the same thing
in both readings, and every row that has one also released something free.

## 8. status.html

Everything about our own process: claim dispositions, coverage gaps, source freshness, bulk
re-dating, releases per week, and when the record starts.

Linked from the footer, out of the way of the common visit. Obeys the reader's theme.

## Navigation, history and the address bar

**Navigation goes in the URL; preference does not.** What moves a reader somewhere is the tab, the
period being read, and opening a work's record. Each pushes a history entry, so Back undoes it.
Everything else stays out: language, theme, romanisation, furigana and compact/detailed are
preferences, and Back flipping a reader's language would be a bug.

Filters and sort are deliberately not in the URL yet. They carry a weaker expectation than the
three above, and pushing on every adjustment fills the history stack so that leaving the site takes
a dozen presses. If they are added, the rule should be to push on the first application of a filter
and replace on later adjustment of the same one.

**The URL wins over the saved view, and the order is the whole of how.** `restoreView()` clicks the
saved tab, that click calls `navSync`, and `navSync` rewrites the address from what is on screen.
Reading `location.search` afterwards therefore returns the view just restored rather than the link
that was followed. That destroyed every deep link, and it was written into the code by the same
commit whose comment warned against it. Read the address first, and run the restore with
`NAV_APPLYING` set so it cannot push an entry of its own.

The address also describes only what is visible. A period means something on the updates tab and an
open record on the volumes tab, so neither is carried into a URL for a different tab. The DOM keeps
the record open behind the scenes; the address stops claiming it.

**Shareability is the larger gain.** Before this every address was identical, so no view could be
linked to at all. Deep links change no indexing posture: `robots.txt` and the `noindex` meta stand.

## Before changing the layout

Ask which of these a control is, because the answer decides where it belongs and whether it is
navigable:

- **Selects a body of data** (period, tab, a record) is navigation. It goes near the top, it gets a
  history entry, and it belongs in the URL.
- **Narrows the current body** (platform, kind, access, search) is a filter. It sits with the other
  filters and is not in history today.
- **Changes how the same data looks** (language, theme, romanisation, furigana, compact) is a
  preference. It is persisted, never in history, and sits apart from the filters.
- **Leaves the site** (a link to a chapter on the publisher's platform) needs nothing from us. The
  browser gives it history already, and Back does the right thing.

The period selector was at the foot of the updates tab, below the list it governed, which put the
most navigational control furthest from every other control and read as an afterthought. It is
first in the bar now, as a calendar grid rather than an option list, because the list grows by
twelve entries a year.

## The period selector, and the one prediction

**The button says what you are looking at; the popover says what that means.** "latest" rather than
"last 14 days": the widest control in the bar should not spend itself on a number a reader rarely
needs, and a default view labelled with a window length reads as a filter. The window length sits
in the popover, where the choice is made.

**"coming soon" is the only place this interface states something that has not happened.** It is
calculated from each series' own mean interval, needs three chapters before an interval means
anything, and carries a note above the list saying it is inferred, in the same style used for
generated readings. Its rows carry 更新予定 / Expected rather than 新話, because reusing the chapter
badge would assert that a chapter exists, which is the claim the note disclaims.

Its horizon runs forward only, and that is where it parts from `adapters/schedule.py`. That module
tolerates a prediction three intervals late, because being overdue is a reason to go and
look. It is not a reason to tell a reader something is coming. The first version reused that rule
and offered dates nine months in the past.

## One height per control bar

An input, a select and a button size themselves differently from the same padding, so a bar built
from all three had four heights in one row and read as several rows that happened to be adjacent.
Every control in a `.controls` bar shares one height, set once as a custom property.

Hierarchy stays in weight and colour rather than in size. `reset` is quieter than the filters
beside it; it is not shorter than them.

## Showing which filters are set

Filters persist across sessions, so a reader can return to a list already narrowed by a choice they
have forgotten making. Opening to "1 shown of 251" with nothing indicating why is the failure this
prevents: the dropdown responsible looks exactly like the others beside it, and when the bar wraps
it may not even share a line with them.

**What is marked is exactly what reset clears**, taken from one list per tab. Deriving it from
anything else drifts: eventually something is marked that the button does not clear, or something
it does clear is left unmarked. Those lists already excluded the presentation control, which is the
same line §15 draws.

The reset button goes live at the same moment and states how many filters it will clear, so the
mark and the way out are learned together. It is disabled otherwise, which it never was, although
pressing it then did nothing.

Border and weight carry the mark and the text colour is left alone. All three together read as an
alert rather than as a mark, and colour by itself carries the meaning for nobody who cannot see it.

## Search

**Every form of a name is searchable, whichever one is displayed.** The index holds the Japanese
surface, the kana reading, the English name where there is one, and all three romanisations.
Japanese was always findable in either language mode because the box matched the stored Japanese;
English was findable in neither, and 87% of the catalogue renders as romaji in English mode, so a
reader could search only the text the interface was hiding from them.

The rule matters most once a work has a translation. The interface then shows the English name and
hides the romanisation, so indexing what is shown would make translating a title lose the romaji
somebody already knew it by.

Indexing the reading also means a work answers to how it sounds: 百合の花 is found by ゆりのはな
without knowing the kanji.

**Long vowels: index all three romanisations, fold macrons, leave ASCII doubles alone.** Waingāruzu,
Waingaaruzu and Waingaruzu each hit exactly because all three are indexed. Macrons fold on top,
since a reader who sees ā and cannot type it writes a, and ā is never anything but a long a.

Folding ASCII doubles looks symmetrical and is wrong. Titles mix scripts, so collapsing ee turns
Free into Fre, and ゆり and ゆうり are genuinely different words. The doubled romanisation is
indexed in full, which covers the same typing without the damage.

**Spacing is not identity**, on both sides of the comparison. Readings arrive word-separated
(ハル ナツ アキ フユ) and a reader typing ハルナツアキフユ means the same thing, while "bloom into
you" must still match with its spaces. Both are compared stripped as well as intact, in one place,
so a field gets the same treatment whether or not it came through the index builder.

Search does not depend on the romanisation toggle either. A preference about display must not
change which rows exist, or two readers looking at the same database get different answers to one
question.

**It over-matches rather than under-matching.** Once macrons fold, `yuri` finds works read ユリ and
ユウリ alike. A reader can see the results and choose; a work that cannot be found is invisible.

