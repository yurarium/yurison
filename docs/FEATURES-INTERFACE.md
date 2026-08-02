# Interface features

What the reader-facing site does and why. Layer 3 of the authority order: it may not contradict
[Requirements](REQUIREMENTS.md) or [Definitions](DEFINITIONS.md), and the invariants in `check.py`
enforce the parts of it that admit a correct answer.

This is a **record of decisions**, not a plan. `INTERFACE-PLAN.md` was the plan; all four of its
topics are built and it is kept only as history.

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
