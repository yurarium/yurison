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
are not confident in.

The failure mode is a plausible reading with no source behind it, *presented as if it had one* —
indistinguishable from a correct one at a glance. But that is a problem of presentation, not of
guessing, and the project owner's call is that it can be defused by **labelling unverified readings
as unverified**. An acknowledged guess is a different speech act from an assertion: it does not
misname anyone, it offers a reading and says it is a reading. So a guess may be published *provided
it is marked*, and the choice stops being "publish a possible error or show nothing" — which is the
choice that made the perfectionist standard necessary in the first place.

**This is not a reversal of the no-system-uncertainty rule** (see §5d, which explains why).

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

6. **Search, in bulk, deliberately.** Not ruled out — the project owner's position is that a bulk
   query beats not knowing, when the answer for many names is genuinely out there. It only has to be
   done in a way that does not get us blocked, and there is a right and a wrong way:

   - **Use a search API, not the results page.** Scraping a SERP is what triggers blocking, breaks
     terms of service, and yields nothing citable. A proper endpoint (Google's Programmable Search
     JSON API, or Bing/Brave/Kagi equivalents) is metered, contractual, and returns structured
     results. Most are paid past a free daily quota — a real cost to weigh, but a small one at these
     volumes, and it buys legitimacy rather than luck.
   - **One query per name, not per attempt.** Cache the result forever; a name searched is never
     searched again. The daily free quota then sets the pace instead of a rate limiter, which suits
     a task designed to tick over slowly anyway.
   - **Query narrowly.** `"作者名" site:pixiv.net` beats a bare name: fewer requests, better
     precision, and less that looks like scraping.

   Search comes LAST, after the free passes, so it only ever sees the residue.

**Never: scraping a search results page.** That is the specific thing that angers a search engine,
and it is not the same as querying its API.

## 4. Pipeline

Four passes, each cheaper per name than the next, each recording *where the answer came from*.

```
0  cache mining      no network   Latin handles, bylines already in Latin
1  deterministic     no network   kana → Hepburn. 219 authors + 164 titles, exactly, no guessing
2  bulk databases    ~tens of requests, all cached
                     AniList → MangaUpdates → Wikidata, in that order, skipping what is solved
3  automated search  one metered API query per unresolved name, cached forever
4  label the rest    what search could not settle is published UNVERIFIED, not queued
```

**No pass is a pile of names for a person to work through.** Checking hundreds of names by hand is
ruled out, and the plan does not depend on it anywhere: pass 3 is an agent with a search API, and
pass 4 is a labelling rule rather than a task. The residue is *published*, marked unverified per
§5d, and improves whenever a later run finds a source. Nothing waits on a human, and nothing sits in
a queue looking like work that will never be done.

**Self-checkpointing and resumable is a requirement, not a nicety.** This runs for days in the
background and will be interrupted — by a restart, a rate limit, a crash, or simply being told to
stop. So:

- **State lives on disk, not in a process.** Every pass writes `data/names/*.yaml` keyed by the
  Japanese string, flushed as it goes rather than at the end. Killing it at any moment loses at most
  the name in flight.
- **Resolved is final.** A name with an answer is never re-queried, so a restart resumes rather than
  repeats. This is what makes the total cost bounded no matter how many times it is stopped.
- **Attempts are recorded too, not just successes.** A name that was searched and found nothing must
  be marked as searched, or every restart pays for it again — and it is also how §4a's "closed,
  nothing to find" bucket gets populated instead of looking like permanent outstanding work.
- **Every external response is cached to disk** before it is parsed, so re-parsing after a bug fix
  costs nothing and the whole job can be re-derived offline.
- **Progress is legible from outside** — a count of resolved / attempted / remaining per pass, so
  "is it still working" is answerable without reading a log.

## 4a. How long, and how much of it is searching

Measured where possible, estimated where not, and the estimates are marked as such.

**Pass 0 yields less than §3 implies — I checked.** Sampling 278 cached pages across seven caches,
65% contain a Latin social handle, which looked encouraging until the handles were counted per host:
almost all are the *platform's* own footer links. Filtering out any handle appearing on more than
half a host's pages leaves **0% for kadokomi and pixiv, 5% for niconico, 30% for GigaViewer** — and
even that 30% still contains platform accounts (`SundayWebry`, `comicdays_team`) alongside genuine
author ones (`jiangsal` is Sal Jiang, an author we hold). Realistic yield after filtering: **5–15% of
authors**. Worth doing because it is free and the handles it does find are authoritative, but it is
not the shortcut it looked like.

**Ruby furigana in our caches: 0 of 278 pages.** That source does not exist. Every reading has to
come from a dictionary, a database, or the alignment pass.

| pass | network | time | resolves (estimated) |
|---|---|---|---|
| 0 cache mining | none | ~1h incl. writing it | 50–100 authors |
| 1 kana → Hepburn | none | minutes | 219 authors, 164 titles — *exact, not estimated* |
| 2 bulk APIs | ~800–1500 requests | 2–4h at polite pacing | 25–35% of titles, similar for authors |
| 3 automated search | 1 metered query per name | **the long tail** | most of the remainder |
| 4 label the rest | none | none — it is a rule | the hard core, published unverified |

**Pass 2's request count is small and its coverage is the uncertainty.** AniList batches via
aliases, so 1055 titles is ~40 requests, not 1055. The doubt is coverage: our set is 415 one-shots
and ~640 serials, and these databases index tankōbon-bearing series well, web-only serials
moderately, and one-shots barely at all. A weighted guess is 300–370 titles resolved, leaving
~700.

**Pass 3 is where the time goes: roughly 600–700 titles and 450–550 authors.** Fully automated —
one narrow search query per unresolved name, plus the work's own page where that helps, both cached
forever. Wall-clock is set by the search API's daily quota rather than by compute: at a free tier of
~100 queries/day this is a couple of weeks of ticking over; with a paid tier it is hours. Either way
it is **unattended**, which is the point.

**Searching, specifically: close to zero by design.** §3 rules out bulk search-engine queries, so
the traffic is documented API calls plus publisher pages we largely already hold. Net new fetches
are on the order of a single adapter run — not a bot-block risk at one request at a time.

**The hard core.** Some fraction — a guess, not a measurement — will not be resolvable at all: a web
one-shot by an artist with no tankōbon, no database entry and no English-language presence has no
official English name and no published reading anywhere. These are not a backlog. They get a
best-guess reading **labelled unverified** (§5d), and where not even a guess is defensible they get
the mechanical romanisation §6a describes, also labelled. Both are finished states. The one thing
they must not become is a list of hundreds of names waiting for a person.

**Deliberately out of v1: OCR of title-page art.** §1 notes an official English title may exist only
in the logo artwork. Reaching it means fetching images and running OCR over them, which is a
different order of cost and a different failure mode. Leave it; record which works are suspected to
have one.

## 5. What gets marked

Per the project owner: series names need their official/guess status shown; author names do not,
because correct romanisation is sufficient where the author has stated no preference.

**Titles** carry an English rendering plus a `basis`:

| basis | meaning | shown as |
|---|---|---|
| `official-jp` | the English title the **author, magazine or Japanese publisher** themselves use — an `og:title`, an English page, the title-page art. The work's own name in English | no mark |
| `licensed` | what an **English-language licensor** publishes it as (Yen Press, Seven Seas, Viz, Kodansha USA). Authoritative, but a second party's choice | no mark |
| `translated` | our rendering of the meaning | marked |
| `romaji` | Hepburn of the Japanese, where a translation is the wrong answer (§5a) | marked |

**Precedence: `official-jp` > `licensed` > ours.** Where a work has both an official-jp and a
licensed title and they differ, keep both and show the official-jp one; the licensor renamed it, and
the name the work was given at home is the better answer. Do not discard the loser — a reader who
knows it by the licensed name still needs to find it.

**Fan translations and scanlation titles are excluded entirely.** Not ranked last, not a fallback,
not recorded as a lead. They are not a name the work has: they are unauthorised, frequently several
competing versions exist, and recording one lends it an authority it does not have. This is a
bright line, not a preference.

> **Consequence for §3's sources, and it is not small.** MangaUpdates is largely a
> scanlation-community database and its English titles frequently ARE fan names; AniList's
> `title.english` is community-editable and usually but not reliably the licensed title. So neither
> can establish `official-jp` or `licensed` on its own authority. Both remain excellent for
> ROMANISATION and for matching a work to an identity — the jobs they are actually good at — but an
> English title from either is an unconfirmed candidate until a Japanese publisher page or a
> licensor catalogue corroborates it. Provenance must therefore be recorded per title, not just the
> string: without it, a community edit and a licensor's catalogue entry are indistinguishable six
> months later.

`official` is unmarked precisely because it is not our claim. The other two are, and a reader should
be able to tell that a title is ours rather than the book's. One mark covering both non-official
cases is probably enough; the `basis` field keeps the distinction in the data whether or not the
interface renders it.

**Authors** carry the rendering and a basis (`stated` / `romaji`), but no visible mark either way —
both are just the person's name. The basis exists so that a stated preference is never overwritten
by a later mechanical pass. `stated` means the AUTHOR stated it: a community-supplied romanisation
in a fan database is not a stated preference, however confident it looks.

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
- **suppress it when the two lines would say the same thing.** A row whose only English is the
  mechanical romanisation of its own Japanese is one name written twice, so 両 mode should show it
  the way it shows a title already in Latin.
- **authors need no second line at all.** A romanisation and its Japanese are the same name twice;
  one is enough, chosen by the toggle.

That leaves the doubled row for the case that actually earns it — a work with a real English name
that a reader might know it by. A reasonable expectation is that this is a minority of rows even
once the work is done, which makes 両 mode affordable rather than a mode that doubles the page.

## 5d. Why an "unverified reading" mark is allowed when 要確認 was not

This project removed 要確認 from the reader interface on the principle that **uncertainty about our
own collection process is a category error to show a reader** — nothing but the system will ever
check whether a listing site's claim was confirmed, so the mark asked the wrong audience to hold an
open question. A mark on an unverified reading looks like the same thing. It is not, for three
reasons worth writing down so this does not get "tidied up" later by someone applying the rule
mechanically:

1. **It is a fact about the content, not about our process.** 要確認 meant "we have not checked this
   yet". An unverified reading means "this name may be pronounced another way" — a property of the
   name, of the same kind as a publication date the platform itself moved, which the interface
   already keeps.
2. **The reader CAN adjudicate it.** A Japanese-literate reader looking at 樫風 knows whether our
   reading is plausible; many will know it outright. That is precisely what was untrue of 要確認.
3. **It protects a third party.** The other marks were about our confidence. This one exists so
   that a real person is not authoritatively misnamed under their own work. Removing it does not
   simplify the interface, it transfers a cost onto someone who did not consent to it.

Concretely: readings carry `verified: true|false`, and the interface distinguishes them — the exact
treatment can be quiet (an unobtrusive marker or styling) since the common case should be verified.
Unverified is a **temporary state that a later confirmation clears**, so it must never be conflated
with the floor in §6a, which is the different statement "no source states how this is read".

## 6a. An English page has a floor, and the floor is not Japanese

**Ruled by the project owner, 2026-08-09, overruling what §5 and §6 said before it.** Showing
incorrect kana in Japanese is the least acceptable thing this project can do. Showing an unclear
romanisation in English, with a tooltip explaining that it is unclear, is **required** as an
alternative to Japanese text appearing under an English heading.

So there is no surface where Japanese is a finished state in English mode. Where the store holds a
reading, the name is spelled from the reading. Where it holds nothing, `adapters/names/romfloor.py`
spells the characters: a run of kana romanises mechanically, a run of kanji is read by the analyser
or, failing that, character by character, and a credit ending in 編集部 has its magazine read and
its department translated. Every string this produces carries a mark and a tooltip saying the
reading is not attested, and `check.py` refuses to let that mark be quietly removed.

**The asymmetry is deliberate and is the same one §5d turns on.** None of this touches the Japanese
side. Furigana and kana are unchanged, because a reader in Japanese has the name itself and can
judge our reading against it, and a reader in English has the romanisation and nothing else.

**What is measured.** `English mode has no Japanese` is an invariant over every rendering surface
and blocks at zero. `renderings resting on a mechanical romanisation` counts the names carrying our
guess instead of somebody's reading, which is the data gap written as a number: it falls only as
readings are researched and nothing about the renderer can move it.

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

### A rule tried and rejected: dividing the surface by the reading's word spacing

Recorded on 2026-08-08 so it is not derived a third time. `kana.align('毎月庭つき大家つき',
'マイツキ ニワツキ オオヤツキ')` puts 毎月庭 under マイ and 大家 under ニワツキオオヤ, and a person
reads that title without difficulty, so there ought to be a rule. The reading is three
space-separated words and those spaces come from the analyser, which found them by dividing the
SURFACE. So the proposal was to read them as a division of the pair: one reading word to one
surface unit, in order, with okurigana settled inside each unit where the question is small.

It is implemented in fifty lines and it does not work, and the reason is worth keeping.

**The spacing does not say WHERE the surface divides.** 毎月庭 is one unbroken kanji run split
between two reading words, and マイツキ|ニワ can be cut as 毎|月庭 or as 毎月|庭, and both spell the
reading. Choosing between them needs to know that 毎月 is a word, which is
lexical knowledge this module deliberately does not carry (it would be the KANJIDIC2 dependency
§5c avoids). Trying the longest unit first and refusing any run that reads as fewer morae than it
has kanji picks the human reading here, and picks a wrong one elsewhere: 冬木先輩 against
`フユキ センパイ` comes out 冬木先 under フユキ and 輩 under センパイ, which `test_kana.py` had
already pinned as the counter-case from an earlier round.

Measured over the 5,435 readings in the store, segmentation alone raises the placements holding
fewer kana than they have kanji from 30 to 296, because dividing correctly and then splitting each
unit by first fit is worse than not dividing at all. Adding the mora floor brings that to 24, below
where it started, while cutting 939 kanji runs the old answer kept whole. Some of those cuts are
right (2週間 becomes 2 and 週間) and some are 女社長 becoming 女社 and 長. The corpus number
improved while a pinned counter-case broke, which is the shape STANDING-INSTRUCTIONS §2 warns
about.

**The information was thrown away upstream, and that is where to look.**
`pass4_analyser`
tokenises, aligns each token separately and gets both 毎月|庭|大家 and 冬木|先輩 right, because
SudachiPy hands it the token SURFACES beside the readings. The store keeps only the readings joined
with spaces, so `kana.align` on a whole string is re-deriving a division somebody already had. The
records this fallback serves are the ones whose reading came from a source with no token structure
at all, and for those the division was never known, so no rule inside this module can recover it.
The fix, if it is worth making, is to keep the analyser's division beside the reading rather than
to guess it back.

### 5e. Where a person's name divides is a second fact, and it has its own sources

Recorded 2026-08-09, after 太陽まりい was reported reading `Taiyōmarii` as one word.

**The reading can be right and the division still missing.** The media-arts catalogue files that
artist タイヨウマリイ, which is correct, and files it closed up. A romanisation is spelled out of
the reading, so a reading with no space in it produces a Latin name with no space in it, and the
person is 太陽 まりい. `いがらしゆみこ` had been in the same state since the first hour of this
project, when the owner said "surely on general principles, Igarashi Yumiko".

So a record can be settled about how a name is SAID and say nothing about where it BREAKS, and
until now only one of those two questions was being asked. §5c's rejected rule and the one above it
are both attempts to answer the second from the characters, and neither can: a kana name has no
kanji boundary to lean on and an undivided reading has no boundary at all.

**Which sources hold it, measured rather than assumed.** Every route below was tried against the
459 author records whose reading is one unbroken run.

| route | on disk | what it gave |
|---|---|---|
| openBD `collationkey` | yes | already mined; a comma per person, 372 people, 8 still glued for other reasons |
| MADB `schema:creator` | yes | 436,431 creator readings, 8,824 with a space, 2 of ours |
| Wikidata P734/P735 | yes | 154 records hold `reading_family`, 1 of them settles a name |
| our own store, another spelling | yes | 4, each the same artist filed twice |
| platform and shop bylines | yes | まんが王国 and ヤンマガWeb print the kana closed up |
| **NDL 著者標目** | one request | the answer, and it also divides the SURFACE |

**The heading is the route, and it was open the whole time.** A record page under `/books/` prints
`美術制作者 ： 美鈴, ちょこ ミレイ, チョコ ( 034528963 )典拠`: the surname, the given name, and the
same division of the reading, from a cataloguing authority, with the authority record's own number
beside it. `ndl_books.py` had been parsing those pages for a title's reading since the day before
and reading past this field. STANDING-INSTRUCTIONS §14c is about exactly this shape, where one use
of a route has been mistaken for all of them.

**What is taken is the offsets and nothing else.** A heading is a filing form before it is a
pronunciation and it folds the kana that sort together, so `boundary.carry` puts the division onto
the kana we already hold and refuses unless the two correspond character for character.
`adapters/names/ndl_heading.py` holds the parse and `data/fixtures/ndl/` holds four real headings,
including the one that must be refused: searching by author for いがらしゆみこ returns 五十嵐 由美子
as well, a different spelling read the same way.

**Where nothing states a division the run-on form stands, and is marked.** In Japanese the reader
has the name itself; in English the Latin string is all there is, so it carries a note saying no
source states where the name divides. That is the §5d asymmetry applied to a second fact, and the
budget `author names romanised as one word` counts what is left. It will never reach zero, because
こかむも is one word and the publisher's own cover says so.

**Show the Japanese.** This is the same rule `platName()` already follows for platforms — absent
from the map means it passes through untouched — and it extends the project's standing principle
that absence is a state rather than a blank to be filled.

Specifically, never do any of these: romanise kanji by guessing a reading (東雲 is Shinonome, but
樫風 could be several things and a wrong reading is worse than no reading); machine-translate a
title into an English name and present it as the work's name; or leave a row empty. A new work
appearing tomorrow renders in Japanese, looks deliberate, and joins the queue.

### 5f. The other half: a division nobody stated, which an analyser had already made

Recorded 2026-08-09, after のぴやか梢 was reported reading `No Pi Ya Ka Kozue`.

§5e is about a name with no division in it. This is about a name with the wrong one. 279 author
records carried a division a morphological analyser produced and no source anywhere had stated, and
the analyser is at its very worst here: SudachiPy met のぴやか梢, a pen name it has never seen, and
handed back one token per kana. The invariant `a division cites its source` had existed since the
kana work and tested kana surfaces only, so not one of these was covered by it.

**A wrong division is worse than no division.** `Nopiyakakozue` with the §5d note beside it says
nothing about where the name breaks and says so. `No Pi Ya Ka Kozue` says the name breaks in four
places, under the artist's own work, on the authority of nobody.

**What the surface can settle, and what it cannot.** A kana run in the surface reads as itself, so
its length in the reading is arithmetic: のぴやか is four morae and ノピヤカコズエ opens with exactly
those four. That fixes WHERE a division falls. It does not say THAT one falls, and the difference is
the whole safety argument, because 九羊ボン is filed クラムボン by the media-arts catalogue and the
same arithmetic would cut it in half before ボン. So the rule only ever removes spaces:
`adapters/names/analyser_division.py` takes out every space the surface does not account for and
proposes none, and 九羊ボン's reading arrives from the catalogue with no space in it and leaves with
none. 194 records were corrected, 134 of them to a name with no division at all, and 67 divide
exactly where their own surface says and now record the surface as the source.

**A symbol reads as itself too, and that is where the arithmetic goes wrong.** R-指定 read
`R - Shitei`, 2C=がろあ read `2 C =Garo A` and あんじんねこ@創作 read `Anjin Neko @ Sōsaku`, each
because punctuation passes through a reading untouched and the offsets beside it are therefore just
as computable. A symbol is not an element of a name, so a surviving offset needs a word character on
each side of it.

**Titles and publishers share the analyser and not the fault.** A title is a sentence and a
publisher is a company, both made of ordinary words, which is what a morphological analyser is
built for and good at: `100万円貰った女子高生の話` reads `Ichireireiman En Moratta Joshikōsei no
Hanashi` and 空色の音 reads `Sorairo no Oto`. Their spacing is also load-bearing in a way a person's
is not, since `kana.align` reads it to place ruby (§5c). §1 already keeps the two standards apart
and this is the same line: an analyser dividing a phrase is doing its job, and an analyser dividing
a person is guessing at the thing §5c names as its weak point. 2,532 title readings and 9 publisher
readings hold an analyser's division and all of them stay.

**A rule tried and rejected**, so it is not re-derived. Collapsing the whole reading whenever any
one of its spaces was unsupported. It is simpler to state and it throws away answers that cost
nothing: むつをむつ 蒼井ゆん would lose ムツヲムツ アオイ ユン, where the surface establishes both
offsets, and 4ka エンピツ would lose the space its own byline writes.

### 5g. What kind of evidence Wikidata is, and where a division is written down

Two rulings taken 2026-08-09, both about what a record is entitled to claim and whether anything
can read the claim.

**Wikidata states a reading and states no name.** 67 author readings were sourced to it carrying
`reading_basis: stated` and no `reading_source_kind` at all, so the source sat outside
`curate.READING_ATTRIBUTION` and the table that says what may be believed had nothing to say about
it. The kind is `community-db`, which is what the same module already writes for every other fact it
takes from Wikidata. What the table now records is the line that makes it admissible: **P1814 prints
kana.** A reading is a transcription anybody Japanese-literate can weigh against the characters,
which §5d already builds the interface around, and a user-edited knowledge base has no standing over
a person's name while being perfectly able to print their kana. Its English label is a different
claim and is refused exactly as before.

That admits one community database and not three, and the line is between kana and Latin. AniList
and MangaUpdates return romanised strings, so a reading from either is recovered by reading a
romanisation backwards, which has already lost the length of every vowel. Those are
`back-converted`, the attribution table carries no row for them, and `boundary.SETTLED_BASES`
refuses them as the donor of a division on the same reasoning.

**Where a name divides is a field, and it was half in prose.** §5e made the division a second fact
and `boundary.fill` records it in `reading_boundary`. `ndl_heading.entry` and
`openbd_reading.boundary_entries` recorded the identical fact in `reading_note`, so 293 author
records stated their division in a sentence and left the field empty. A sentence cannot be queried,
counted or checked, so every measure reading the field read those records as having no source at
all, and no number anywhere could tell 293 from 0. This is STANDING-INSTRUCTIONS §3 with the two
producers one round apart.

The field is the only slot now. A record has two honest ways to account for the spaces in its
reading and `reading_source_kind` decides which: where a source supplied the kana it supplied the
spaces in them, so an NDL transcription or an openBD collationkey cites itself; where the kana are
ours, nothing came with them and the donor is named in `reading_boundary`. The invariant
`a division names its donor in a field` holds it, and the note keeps the argument, which is what a
note is for and what no field was going to hold.

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
6. **The work runs automatically end to end, for names AND titles.** Passes 0–3 resolve what they
   can; pass 4 labels what is left. Difficult cases are *reported* at the finish so the shape of
   them is known, but the report is information, not a worklist — **checking hundreds of names by
   hand is ruled out**, and nothing in this plan depends on it.

   That ruling is what §5d's unverified label buys. Without it the only honest options for an
   unsourced reading are silence or a hand check; with it there is a third, and it is the one that
   scales.

## 9. Still open

- Nothing blocking. The residue report from §8.6 is what informs the next decision.
