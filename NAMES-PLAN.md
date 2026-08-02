# English names for works and authors — plan

Not started. Scope is the WEB case — the 更新 and 作品 tabs. The 302 print works are set aside and
will come back later; they are also the easy half, for a reason worth recording (§2).

## 1. The job is two different problems wearing one name

**Authors are MOSTLY a reading problem.** 東雲水生 is not translated into English, it is *read* —
Shinonome Mizuki — and once the reading is known the romanisation is mechanical. The difficulty is
that Japanese personal names are ambiguous by design: the same kanji take several readings and a pen
name can choose any of them. There is no algorithm. Either a source states the reading or we do not
have it.

**A wrong reading is not a typo, it is an insult.** Japanese name readings are frequently
non-unique — the same kanji legitimately take several — and getting one wrong misnames a real person
in public, under their own work. That is a reputational cost to them and to this database, and it is
not symmetrical with the cost of leaving a name in Japanese, which costs nothing. So the standard
here is **as close to perfect as can be researched**, not best-effort: a reading is published when a
source states it, and corroboration from a second source is worth the extra request for any name we
are not confident in. A plausible-looking reading with no source behind it is exactly the failure
mode to design against, because it is indistinguishable from a correct one at a glance.

And a reading is not the whole answer either, because **people have their own preferred
romanisation** and
it is not always the one Hepburn produces. An author may spell themselves Inouye rather than Inoue,
may lower-case a pen name, may use English word order, may pick a Latin name that is not a
transliteration of the Japanese at all. Where that preference is visible — a handle, a signature, a
Latin byline, an English-language interview — **it is their name and it outranks anything we
compute**. Mechanical romanisation is the fallback, not the goal, and so an author rendering carries
a basis in the data (`stated` vs `romaji`) even though neither is marked in the interface. The point
of recording it is to know which ones we must never silently overwrite with a computed form.

**Titles are both.** Some works have an official English title, which is a fact to look up. The rest
have no English name at all, and we render one ourselves. That difference is why titles need marking
and names do not.

**"Official" is not the same as "licensed", and this is the trap.** A licensed work has an official
English title in a catalogue, findable in seconds. But plenty of *unlicensed* Japanese web manga also
carry an official English name — chosen by the author or the magazine — and it can be much harder to
find, because it may exist only **baked into the title-page artwork or the series logo**, where no
amount of text scraping will reach it. Others hide in an `og:title`, an English-language special
page, or the author's own usage on social media. So the search for an official title cannot stop at
the licensor catalogues, and a work returning nothing there is *not* evidence that no official
English name exists — only that we have not found one. Anything we generate must stay overwritable
by a later sighting of the real thing.

## 2. The numbers, measured 2026-08-02

Web authors — **965 distinct**, 810 of them on exactly one work:

| | n | |
|---|---:|---|
| already Latin | 60 | nothing to do — `Sal Jiang` is already the author's own rendering |
| kana only | 219 | **mechanically romanisable**, no lookup at all |
| contains kanji | 670 | needs a stated reading from somewhere |
| mixed | 16 | case by case |

Web titles — **1055 distinct**: 19 Latin, 164 kana only, 817 with kanji, 55 mixed.

So roughly **29% of authors are free** and 69% need a source. That ratio is the whole planning
problem, and it is why this cannot be a pile of web searches: 670 names at even one search each is
both slow and exactly the traffic shape that gets an IP blocked.

For contrast, and for when the print works come back: MADB and openBD both carry kana readings
already, and we are throwing them away. openBD gives
`PersonName: {content: "林家, 志弦", collationkey: "ハヤシヤ, シズル"}` and the same `collationkey`
on every title; MADB gives `title: {ja, yomi}`. Those 302 works are a re-parse of data already on
disk, not research. **Do not spend a single network request on the print half.**

## 3. Bulk sources, best first

Ranked by names-per-request, which is the only metric that matters here.

1. **Our own caches — zero requests.** `giga-cache/`, `pixiv-cache/`, `comici`/`webpages` caches and
   the rest already hold the pages these authors were read from. Two things are in them that we did
   not extract: **Latin handles** (an X/pixiv handle next to a byline is the author's *own* Latin
   rendering and outranks anything we would compute) and **furigana**, which some platforms print as
   ruby over a byline. This is free and must be done first — it also shrinks every later query.
2. **AniList GraphQL** — the best single external source for this case. Public, documented, no key,
   ~90 req/min, and *aliases let many lookups ride in one request*, so 1055 titles is tens of
   requests rather than a thousand. Returns `title { romaji english native }` and
   `staff { name { full native } }` — romaji AND official English AND the author, in one place.
   Coverage of web-serialised yuri is partial but real.
3. **MangaUpdates API** — better tail coverage of web/indie series than AniList, with romanised
   titles and author names. Worth running second, only for what AniList missed.
4. **Wikidata (SPARQL, or a dump)** — CC0, one query can carry a `VALUES` list of hundreds of
   titles, returns official English labels and en.wikipedia sitelinks. Thin for web-only works but
   authoritative where it hits, and the licence is unambiguous.
5. **Publisher/licensor catalogues** (Yen Press, Seven Seas, Viz, Kodansha USA) — the definition of
   an *official* English title, but they only cover licensed works, which is a small slice here.

**Not on the list: search engines.** Bulk querying a search engine is the one approach that will get
us blocked, gives no licence to the result, and cannot be cached honestly. If a name genuinely needs
a human to look it up, it goes on a queue and waits — see §6.

## 4. Pipeline

Four passes, each cheaper per name than the next, each recording *where the answer came from*.

```
0  cache mining      no network   Latin handles, ruby furigana, bylines already in Latin
1  deterministic     no network   kana → Hepburn. 219 authors + 164 titles, exactly, no guessing
2  bulk databases    ~tens of requests, all cached
                     AniList → MangaUpdates → Wikidata, in that order, skipping what is solved
3  queue             the residue. Never guessed, never invented.
```

Passes 0–2 are resumable and idempotent; each writes `data/names/*.yaml` keyed by the Japanese
string, and a name already resolved is never re-queried. Being resumable is what makes this safe to
run slowly in the background over days.

## 5. What gets marked

Per the project owner: series names need their official/guess status shown; author names do not,
because correct romanisation is sufficient where the author has stated no preference.

**Titles** carry an English rendering plus a `basis`:

| basis | meaning | shown as |
|---|---|---|
| `official` | the author, magazine or licensor uses this English title — from a catalogue, an `og:title`, an English page, or read off the title-page art | no mark — it is the work's name |
| `translated` | our rendering of the meaning | marked |
| `romaji` | Hepburn of the Japanese, where a translation is the wrong answer (§5a) | marked |

`official` is unmarked precisely because it is not our claim. The other two are, and a reader should
be able to tell that a title is ours rather than the book's. One mark covering both non-official
cases is probably enough; the `basis` field keeps the distinction in the data whether or not the
interface renders it.

**Authors** carry the rendering and a basis (`stated` / `romaji`), but no visible mark either way —
both are just the person's name. The basis exists so that a stated preference is never overwritten
by a later mechanical pass.

### 5a. Translation is the default; romaji is the edge case

Project owner's call: **translate in principle**, since a romanisation tells an English reader
nothing about what the work is. But there are titles where translating is the wrong move and the
rule needs somewhere to put them:

- the title is a **name** — a character, a place, a band. *Otherside Picnic* translates; *ゆるゆり*
  does not, it is a coinage.
- the title is **wordplay, a pun, or a rhythm** that dies in translation and whose English version
  would be a different joke, or none.
- the title is **already partly Latin** and the Latin part is the point.
- there is **more than one defensible reading** and picking one asserts an interpretation the work
  does not.

These take `romaji`, and the queue should let a reviewer move a title between the two rather than
forcing the generator to be right first time. A machine translation is never published unreviewed —
that is how a database ends up asserting a plot.

## 5b. What 両 mode costs, and how not to pay it everywhere

> Provisional by agreement: the doubled-row design is easier to judge once names actually exist, so
> it is expected to be refined after the rest is in place. What follows is the starting position,
> not a settled layout.

Rendering follows the existing toggle: **JA** shows Japanese, **EN** shows English, **両** shows
both. For badges that is already settled — `L()` picks one language because a badge sits in a fixed
slot. A title is different: it is the row's anchor, it is long, and in 両 mode there are genuinely
two of them.

So yes — **両 mode implies a second line per row**, and pretending otherwise by running the two
titles together inline would be worse. 怪異部〜M県Y市の怪現象について〜 plus an English title on one
line wraps on any phone, and a wrapped title reads as two entries; the compact list already has a
`.stacked` measurement pass fighting exactly that problem. A deliberate secondary line, dimmer and
smaller, is predictable where wrapping is not.

The cost is worth capping, because most rows do not need it:

- **suppress the second line when there is nothing to add** — the title is already Latin, or our
  rendering is identical to the Japanese. `platName()` established this shape: absent from the map
  means it passes through untouched, and no row should carry a duplicate of itself.
- **suppress it when we have no rendering yet.** Under §6 the row is Japanese-only anyway, and in 両
  mode that should look like a normal row, not a row with a gap where English should be.
- **authors need no second line at all.** A romanisation and its Japanese are the same name twice;
  one is enough, chosen by the toggle.

That leaves the doubled row for the case that actually earns it — a work with a real English name
that a reader might know it by. A reasonable expectation is that this is a minority of rows even
once the work is done, which makes 両 mode affordable rather than a mode that doubles the page.

## 5c. Furigana on series names — the same research, a second use

Proposed as a fold-in, and it is a good one: **to romanise a title you must first know how it is
read, and furigana is that reading made visible.** The lookup, the queue and the storage decision in
§8.1 (store the reading, render the style) all serve both features. Doing them separately would mean
researching the same 817 kanji-bearing titles twice.

Optional, like the taste controls — off by default, persisted per reader.

**The standards differ, deliberately.** §1 sets a near-perfect bar for author readings because a
wrong one misnames a real person in public. The project owner's call is that series furigana may go
out on a **best-guess basis where the reading is not known**, and that asymmetry is right: a
mis-read title is a small, correctable error about a book, not about a person. Two carve-outs
follow from the same reasoning, though —

- a title that **is** a person's name, or contains one, inherits the higher bar;
- a guessed reading is recorded as guessed, so that a later confirmed reading can replace it and so
  that the residue report (§8.6) can list what is still unverified.

**The alignment is a solved problem — use a library, do not invent one.** A whole-string reading is
what the sources give: MADB returns `私の世界を構成する塵のような何か。` → `ワタクシ ノ セカイ オ
コウセイ スル チリ ノ ヨウナ ナニカ`. Ruby needs each kanji run paired with its own kana —
`<ruby>塵<rt>ちり</rt></ruby>` — and that pairing is not in the data. It is also a well-studied
problem with a standard shape: **dynamic-programming alignment of the surface against its reading**,
anchored on the kana that appear in both (okurigana and particles are fixed points), scoring
candidate readings per kanji from a reading lexicon and handling rendaku. Existing tooling:

Licences checked 2026-08-02, from each project's own declaration:

| | licence | |
|---|---|---|
| `SudachiPy` | **Apache-2.0** | tokenising + per-token readings |
| `SudachiDict-core` | **Apache-2.0** | the dictionary behind it |
| `fugashi` | **MIT AND BSD-3-Clause** | MeCab wrapper; the BSD part is bundled MeCab |
| `unidic-lite` | MIT/WTFPL code, **UniDic 2.1.2 itself BSD** | alternative dictionary |
| `cutlet` | **MIT** | Hepburn romanisation — but see below |
| KANJIDIC2 / JMdict | **CC BY-SA 4.0** | per-kanji readings |

**Conclusion: take the permissive stack and skip KANJIDIC2 entirely.** It is the only one with
strings attached — share-alike on modifications, attribution *on each screen* that displays the
data, and a standing obligation to keep the data updated from the latest version. None of that is
onerous, but none of it is necessary either: UniDic (BSD) and SudachiDict (Apache-2.0) both carry
the readings the alignment needs, so the CC BY-SA dependency is avoidable rather than a trade-off to
accept. Everything else is MIT/BSD/Apache, used at build time and never redistributed, so nothing
here makes the database a derivative work — which is the actual test.

**`cutlet` does not support macrons.** Its own documentation lists "macrons or circumflexes: Tōkyō,
Tôkyô" under things it does not do. That does not block §8.1's reader-facing style choice, because
of the decision already taken there: **store the reading, render the style.** Long vowels are
recoverable from kana (ゆう → yū / yuu / yu) so all three styles are ours to generate; cutlet becomes
a convenience for one of them rather than the source of truth. Had we planned to store a romanised
string, this would have quietly capped what the toggle could offer.

**Proper nouns are these tools' weak point, and they are our hard case.** Morphological analysers
are trained on running text and are poor on names and coinages — exactly the 670 author names in
§2. So this tooling largely solves *titles* and largely does not solve *authors*, which is another
reason the two keep separate standards (§1). A tokeniser's confident output on a pen name is not a
sourced reading and must never be recorded as one.

Two levels, and the first is worth shipping on its own:

1. **Whole-string reading**, shown above or beside the title. No alignment, works everywhere, and
   already answers "how do I say this". This is what the romanisation pass produces anyway.
2. **Aligned ruby**, per kanji run. Derivable heuristically: split the surface into kanji and kana
   runs, split the reading on the same kana anchors, and match. The kana in the surface act as
   fixed points, so a title like 私の世界を… aligns cleanly; failures are detectable (leftover runs)
   rather than silent, and a title that will not align falls back to level 1.

Level 2 should never guess an alignment it cannot verify — a ruby annotation over the wrong
character is worse than none, and unlike a whole-string reading it is wrong in a specific, visible
place.

## 6. Fallback for names not yet researched

**Show the Japanese.** This is the same rule `platName()` already follows for platforms — absent
from the map means it passes through untouched — and it extends the project's standing principle
that absence is a state rather than a blank to be filled.

Specifically, never do any of these: romanise kanji by guessing a reading (東雲 is Shinonome, but
樫風 could be several things and a wrong reading is worse than no reading); machine-translate a
title into an English name and present it as the work's name; or leave a row empty. A new work
appearing tomorrow renders in Japanese, looks deliberate, and joins the queue.

## 7. Not getting ourselves blocked

- Documented APIs only, with our existing User-Agent and contact URL.
- Every response cached to disk; a cached name is never re-fetched. The job is re-runnable at no
  cost, which is what makes "slow background task" viable.
- One request at a time per host, with the pacing the adapters already use. No parallel fan-out
  across a single source — the same rule the audit sub-agents followed.
- Batch wherever the API allows it. AniList aliasing is the difference between ~30 requests and
  ~1000 for the same data.
- Resumable by construction, so a run can be stopped and restarted rather than rushed.

## 8. Decided

1. **Romanisation style is a reader preference, not a build-time constant.** Macrons or not — *Yūri*
   / *Yuuri* / *Yuri* — is taste, and the project owner's call is to surface it as a choice **shown
   only when EN is visible**, beside the language and theme controls. That has a consequence worth
   stating early: the data must store the romanisation in a form that can be rendered either way,
   not a baked string. Storing the **kana reading** alongside the name does this for free — macrons,
   doubled vowels and plain vowels are all derivable from it, and none is derivable from the others
   (*Yuri* cannot tell you whether it was ゆり or ゆうり). **Store the reading, render the style.**
2. **Name order** is the same kind of choice and can ride the same control. AniList and
   MangaUpdates disagree with each other, so we must record which order a fetched name came in
   rather than assuming; storing family and given parts separately where a source distinguishes
   them keeps both orders available.
3. **Untranslated titles get a translation in principle**, with the edge cases in §5a taking romaji
   instead. Nothing machine-translated is published unreviewed.
4. **Rendering mirrors the toggle exactly** — JA / EN / both — with the row-doubling cost analysed
   and capped in §5b.

5. **Taste controls persist per reader**, in localStorage, exactly as theme and language already do.
6. **The work runs automatically, for names AND titles**, and the difficult cases are collected and
   raised at the END rather than interrupting for each one. Passes 0–2 (§4) resolve what they can
   without asking; everything they cannot — no source, conflicting sources, a reading we are not
   confident in, a title where translation and romaji are both defensible — lands in one report at
   the finish. How to handle that residue on an ongoing basis is then decided from the actual
   shape of it, rather than guessed at now.

   This is what makes §1's "as close to perfect as can be researched" affordable: the bar is high
   because anything that cannot clear it is *deferred rather than guessed*, and deferring is cheap
   when the fallback (§6) is to show the Japanese and look deliberate.

## 9. Still open

- Nothing blocking. The residue report from §8.6 is what informs the next decision.
