# Working the budgeted gaps, in series

Started 2026-08-08. One gap at a time, each closed by filling it rather than by narrowing what
counts. A gap that cannot be closed is recorded here with the reason, which is a different state
from one nobody has looked at.

**How to resume.** Read the table. The first row not marked done is the next one. Each closed row
names the commit so the reasoning can be found without re-deriving it.

## Order, and why

Value first, where value is what a reader meets, then tractability. Engineering debt is last because
it measures nothing about the data.

| # | budget | at start | state |
|---|---|---:|---|
| 1 | renderings still Japanese in English mode | 334 | in progress |
| 2 | citations withheld from readers | 244 | **done, 36** (an ISBN cites where a query cannot) |
| 2b | the 36 that remain | 36 | queued: 21 reachable via NDL /books/ from a work they are credited on; the other 15 want a platform byline, a shop page or the artist's own account, per §14c |
| 3 | nicovideo works with no rights | 189 | **done, 60** (capture re-run with the fixed pattern; 3 of the residue state only the platform's own ©DWANGO, 57 have no cached page and belong to the capture measure) |
| 4 | imprint strings that reach no line | 139 | **done, 18** (100 were the field repeating its publisher and moved to a measure that says so; 21 genuine lines added; the 18 left are magazines and companies, which are not lines) |
| 5 | one work under two names in a list | 71 | **done, 53** (9 merged on identical title plus shared credit; the rest fold equal with titles that differ, which is where an earlier round found 3 of 41 were bad anchors, so each wants a ruling) |
| 6 | labels with nothing to quote | 49 | **done, 0** (the YH spellings placed on 百合姫コミックス, so the line the reader is shown carries the term; bare IDコミックス still not the yuri line) |
| 7 | credits carrying their own cataloguing | 38 | **examined, unchanged**: this counts a working filter and not a debt. All 38 are a person with a role welded on, correctly withheld so the lookup reaches the person; 34 of the 38 have a person record that reads BETTER than the welded one, which reads the notation aloud (`アオ ト ヒビキ ( エ )` against `アオト ヒビキ`). It falls when captures stop welding, which is upstream in the capture and not curation. |
| 8 | updates naming a work we do not hold | 27 | queued |
| 9 | titles carrying cataloguing punctuation | 23 | **done, 0** (8 editions merged; the measure now counts what a reader is shown and not a record's faithful transcription of an edition; two publisher rulings; the last edition filed under its canonical name) |
| 10 | credits the corpus files as a venue | 20 | **done, 16** (4 ruled companies; the 16 left are artists who self-publish, which the measure was written to expect) |
| 11 | credit fields an identifier does not cover | 19 | queued |
| 12 | unreadable bookwalker rows | 15 | queued |
| 13 | incomplete attested rows | 14 | queued |
| 14 | one page cited for two claims | 12 | queued |
| 15 | undated cmoa candidates | 11 | queued |
| 16 | captures with no floor | 11 | queued |
| 17 | credit pages listing a work that does not name them | 8 | queued |
| 18 | credit identifiers naming nobody | 5 | queued |
| 19 | targets a capture wrote no row for | 4 | queued |
| 20 | titles shorter than their own reading | 3 | queued |
| 21 | names rendered two ways | 2 | queued |
| 22 | scraped counters in chapter names | 1 | queued |

**Held back, and why.** The name backlog (author readings 312, kana divisions 263, works showing a
romanisation 180, titles with no translation 171, works without English 104, uncertain readings 53,
publisher readings 16) has its own task recorded under "search the unsettled names one at a time",
because it is slow by nature and a sweep is what produced the residue. Engineering debt (stock
phrasing 903, invented markup 75, shadowed names 41, adapters off net.py 35, three as an organising
shape 27, interface reads outside an entry point 13) measures the codebase and not the corpus.

**What closing a gap may not mean.** Suppressing a mark, hiding a row, narrowing the measure, or
falling back to a romanisation where a real name is obtainable. A number that falls because the
question got smaller has told nobody anything.

## Wikidata is noncanonical and raises the floor. Ruled 2026-08-09, closed

**The project owner's ruling, verbatim:** "treat wikidata as noncanonical. use it to raise the floor
on romaji, including additional required searches". Setting the question up, earlier the same day:
"I would accept wikidata as an improved basis for any fallback romanisations (with overcoming their
fallback basis)". And the correction, made after the first implementation shipped: "important
correction to wikidata instructions: I mistyped 'without overcoming their fallback basis'".

**So the ruling is: a better string, and not a better claim.** Wikidata may raise the floor on the
romanisation a reader SEES. It does not overcome the fallback basis of the record, so a name resting
on a fallback goes on resting on one and stays in every count of the gap. That is what the rest of
this section is written against; the first implementation read the sentence without the "without"
and had these records leaving the fallback population, which is recorded below because it is the
expensive half of the knowledge.

Wikidata is analogous to Wikipedia. It never STATES a name. It is better than a machine guess and
worse than anything a publisher or the national library prints, and its job is to lift a name off
the mechanical floor. A pass earlier that day had put `community-db` in
`curate.READING_ATTRIBUTION["stated"]`, arguing that a reading is a transcription and a user-edited
base can print kana correctly without having standing over a person's name. The ruling overturns it.

**The basis is `community-printed`**, which says what it is: a community database printed the kana
and nobody with standing over the name has spoken. It outranks `analyser` and `back-converted`, it
sits below `researched`, `surface` and `stated`, and it satisfies no check asking whether a source
stated the reading. `curate.STATED_BASES` is the one list that answers that question and it carries
`stated` alone.

**Where the basis is admitted and where it is refused**, reviewed one list at a time under the
correction. It survives in three places, all of which decide which STRING is used and none of which
decides what a record may claim: `store.READING_RANK` and `build._READING_BASIS`, which pick the
better of two spellings of one person, and `pass4_analyser.wants_reading`, which lets a kana surface
take its own spelling back. It survives in `provenance.SOURCED`, because the Wikidata item page is a
document a reader can open and a marked fallback needs the route to it more than a stated reading
does. It survives in `boundary.SETTLED_BASES`, so a division may still be lent, with
`boundary.donor_basis` naming the origin on the record that receives it. It leaves
`curate.DIVIDING_BASES`, which is the list of bases whose division arrived cited, and it was never
in `curate.STATED_BASES`, `check.STATES_A_READING` or `openbd_reading.SETTLED`, all three of which
the correction reinforces.

**The division stands and is counted, and it is no longer counted as cited.** 68 of the 73 readings
carry P734 and P735, so the kana arrive divided, and 20 more records took a space from one of them
through `boundary.fill`. Refusing the space alone would take the harder half of a single editor's
claim and return 88 people to a glued romanisation. `check.UNCITED_DIVISIONS_COUNTED` is what admits
the basis past `a division cites its source`, beside `back-converted` and for the same reason: a
weak claim is still a claim, and what keeps it honest is a number somebody can watch.
`divisions resting on a community database` is that number, and `reading_boundary_basis` carries the
origin onto a record that borrowed a division rather than leaving it behind on the donor. Filling
that field is no longer enough to count as a citation either, which is the same correction one
record further on: a loan does not make a division cited.

**The mark.** A `community-printed` reading is `verified: false`, so it draws the `[?]` superscript,
whose tooltip says the reading comes from a community-edited database and that no publisher or
library confirms it. Under the correction that superscript carries the floor's own class, which is
the mark every rendering an English page spelled for itself already had, so these names are marked
exactly as a fallback is marked and `renderings resting on a mechanical romanisation` counts them.
The tooltip stays the specific sentence: the class is what the count reads, and naming the database
is what tells a reader where to go and settle it. The dotted underline says a claim is ours or that
a name's division is unknown, and neither is true here.

**The search that followed.** Every author name the project holds or renders has now been offered to
Wikidata: 1,887 names were asked for the first time, in 19 batched requests. It answered with a
reading for 132, of which 126 landed on names openBD, MADB, the National Diet Library or a reviewer
had already settled. Five of those contradicted the stronger source and lost. Six raised the floor.
221 names gained an English label. Four names were never offered, because a publisher, a platform
and the artist's own page had already settled both their reading and their English name.

Wikidata holds almost nothing for the names this project cannot read, and that is the finding. It is
worth having and it is not the route that closes the reading gap.

Note that `boundary.py` still refuses a subset of Wikidata rows for a different reason: some are
MangaUpdates romanisations converted back into kana, which is `back-converted` and never a donor.
That refusal is untouched by the ruling.

**What the budgets did, so the integrator can re-measure against it.** `renderings resting on a
mechanical romanisation` went 44 to 628, which is 584 renderings of the 73 names rejoining the count
they should never have left. `divisions resting on a community database` held at 88 and now carries
the whole weight of the admission, since the invariant stopped treating an anonymous edit as a
citation. Nothing fell.

`credits carrying their own cataloguing` went 38 to 46 for a reason that is not this ruling and is
not a fault either. It counts store records the build publishes no rendering for, and eight records
were added to the store by the round below without a build being run over them, which is what
STANDING-INSTRUCTIONS §14a means by a number that is true of one tree. A build ships all eight and
takes it back to 38. The integrator measures it again on the merge result rather than believing
either figure.

A question the correction raises and does not answer: 1,914 renderings carry `unc` without the floor
class, which is a reading a morphological analyser produced or one assembled character by character.
Those rest on less than a Wikidata edit does, and they sit outside a measure that now counts the
stronger case, which is the shape STANDING-INSTRUCTIONS §14b warns about. `author readings no source
states` counts the 393 records behind them, so the population is not invisible. Whether the floor
class should widen to take the renderings is a ruling nobody has made, and deciding it as a side
effect of this correction is the mistake this correction exists to undo.

## The interpunct in a credit is settled by evidence. Closed 2026-08-09

This was left open by the round above: `pass4_analyser.is_credit_line` refused any string holding an
interpunct, so `くろば・Ｕ` could not enter the name store even though `credits.split_credits` handed
it over whole.

Measuring the class found the larger half of it. ・ is a separator for the splitter that feeds the
store, so seven people were already IN the store cut in half, with a registry identifier minted for
each half, and five of them reached a reader that way: `Kuro Ba, U`, `Sarii, B`, `Jei, Katō`,
`Ana, C, Sanchesu` and `Buririanto, Buraun`.

**What decides it.** A ・ separates people where every piece it separates is credited somewhere else
on its own. The bibliography lists 機動戦士ガンダム 水星の魔女 青春フロンティア as
`HISADAKE / 富野由悠季 / 波多ヒロ / 矢立肇`, which is a source writing 矢立肇・富野由悠季 apart on
the work that joins them, and nothing anywhere credits くろば or Ｕ alone.

**Where the evidence may not come from**, which is the whole of the care in it. The name store and
the credit registry both hold records for くろば and for Ｕ, because the splitter under question put
them there, so a rule that asks either agrees with the split that made it: all twelve strings read as
two people, including the seven that are one. That rule was live, in `creditline`, and it is why the
site drew `Jei, Katō`. `adapters/names/interpunct.py` reads the evidence off credit fields holding no
・ at all, which is 8,812 of the corpus's 8,865 and none of the ones under question.

Two rules were tried and rejected. Script shape, that a ・ separates people where every piece holds a
kanji, gets eleven of twelve right and is wrong about `スタジオクロマト・スタジオコロリド`, two
animation studios with no kanji between them. Piece count, that three pieces means a foreign name,
fits four examples and states nothing.

The residue a person is owed is zero, and `interpunct credits nobody has ruled on` is what says so.
`data/identity/interpunct-rulings.yaml` is where an answer goes, and it is a different file from
`credit-rulings.yaml`, which settles pairs of credits sharing one reading and was here first.

## Make a glued fallback look like a name pair

**Raised by the project owner, 2026-08-09.** `上田香子` renders `Uedakyōko`, which reads as one
token and no reader would take for a Japanese name. The budget `author names romanised as one word`
counts 1,191 of these.

The record says why: `reading_basis: analyser`, `reading_source: sudachi`, and both
`reading_boundary` and `reading_boundary_basis` null. The analyser returned the whole reading as one
opaque guess, so the store cannot say that 上田 is ウエダ with near-certainty while the given name is
open. It holds one claim about the whole string, and the romaniser receives one unspaced run.

The owner asks that these at least take the shape of a plausible family and given pair. Two routes
worth weighing, and the choice belongs to the owner:

1. Record a reading per morpheme, so a surname the analyser is confident about can be spaced off
   while the rest stays glued. This makes the store able to hold a partly known reading, which is
   the thing it currently cannot do, and it serves the other 1,190 as well.
2. Space by the surface's own kanji boundary where the reading aligns, which is arithmetic on
   `上田`+`香子` and states nothing new. `九羊ボン` is filed `クラムボン` and shows why this is unsafe
   in general, so it would need the alignment to be checked rather than assumed.

Neither invents a division from nothing, which the standing ruling forbids. Both need the mark to
stay, since the sounds are still the analyser's.

## A kana name that spells a name from another language

**Raised by the project owner, 2026-08-09.** `ステファン・セジク` renders `Sutefan Sejiku`. The kana are
attested and the romanisation is faithful to them, and the person is Stephen Sedjik or a spelling
near it. Transliterating kana that are themselves a transliteration takes a reader further from the
name than the Japanese did.

Others in the same shape are `アナ・C・サンチェス` (`Ana C Sanchesu`), `ブリリアント・ブラウン`
(`Buririanto Buraun`), `マリコ・タマキ` and `ジリアンタマキ`, who are Canadian, and
`るいす・まくられん` (`Ruisu Makuraren`), which is hiragana and reads as a Scottish surname.

Two pieces of work. Research the underlying Latin spelling, for which a translated edition's
copyright page, the original publisher and the artist's own site are the routes. Then, where the
Latin cannot be settled, mark the rendering and say in the tooltip that the kana spell a name from
another language whose own spelling we have not found, so a reader knows the romanisation is a
transliteration of a transliteration.

The population is small enough to work through one at a time. Note that a name in katakana is not
by itself evidence of a foreign name, since katakana pen names are ordinary, so this needs the same
care as the interpunct rule about what the corpus can actually settle.

## Fold the Latin inside an editorial desk name

`まんがタイムきららＭＡＸ編集部` renders `MangataimukiraraＭＡＸEditorial Department`: the floor
romanises the Japanese and hands the full-width Latin through untouched, with no space where the
desk word begins. `ＮＯＡＨ編集部` is the same shape.

These joined `full-width forms in English renderings` when `creditLine` became a measured surface,
so they are newly counted and not newly wrong. The budget stands at 38 for that reason.

The tolerance the budget exists for is a work published with a full-width sign in its own name,
`2×2＝SHINOBUDEN+` being the case its docstring cites. A desk name is not that: nobody prints
`ＭＡＸ` as a claim about typography, so NFKC folding it costs nothing a reader wants. The spacing
is the other half, since a romanised run and an English common noun run together today.

## Eight researched readings carry no reasoning

Found by the relational schema on 2026-08-09, not by a check. `researched` means a reviewer weighed
evidence, and the argument for admitting that basis at all is that it carries a note saying what was
weighed. These eight say `researched` from `yurarium` and hold no note:

志乃と恋, 明日ちゃんのセーラー服, 梓月は天に咲う, 獄門撫子此処ニ在リ, 由花緒リニューアル,
聖さまの思うままに, 角野兎はかわいい夢を見続ける?, 陰キャギャルでもイキがりたい！

`curate.problems` demands the note and these escaped it, so the enforcement has a hole as well as
the data. Each one is a reading somebody concluded and did not write down why, and the honest
options are to reconstruct the reasoning or to demote the basis.

The schema refuses the row outright, so they are the eight the loader reports as refused. That
number is the fault and not a tolerance.

## Two modules are called store

`adapters/names/store.py` and `adapters/relational/`. Whichever is on the path first wins, which made a
test import the wrong one. One of them should be renamed.

## How a title's honorifics are rendered. Raised 2026-08-10, held for the owner

**Raised by the project owner**, who called the treatment inconsistent and said it may itself be a
"nerd configuration" question, since fans differ. Held rather than decided, with the survey below so
whoever rules has the numbers.

**342 titles are ours to rule on.** A further 32 carry a licensor's English and are not ours to
change. Among ours, `さん` alone is 64 dropped, 63 kept as `-san` and 16 translated: a coin flip.
Across every honorific it is 178 dropped, 91 kept hyphenated, 48 translated to Miss, Lady or Sister,
and 25 kept as an English word (senpai, sensei).

Three policies, any of which beats the present state. Each is stated with what it costs.

**A. Keep every honorific, hyphenated.** `-san`, `-chan`, `-sama`, and `senpai` and `sensei` as
words. This is what most English-language yuri publishing does now. 116 titles already read this way
and 226 would move. It also answers the definite-article question the owner raised the same day: an
honorific carries the definiteness, so `Onee-san Is Interested in Elementary School Girls.` needs no
`The`.

**B. Drop every honorific, translating the relation where it carries meaning.** The cleanest English
and what older licensed practice did. 178 titles already read this way and 164 would move. The cost
is register: お姉さま and お姉ちゃん become one word, and several of these works are about the
difference.

**C. Follow the licensor where one exists and take A otherwise.** The most defensible bibliographic
rule, because it never contradicts a published English name. The cost is that the corpus is then
inconsistent by design, which is the thing being complained about.

**The recommendation is A**, and item 18 below belongs to it.

### One term, three treatments, which is the same fault at a smaller scale

`地雷系` reaches a reader three ways in three titles: `Jirai-kei` hyphenated, `Jiraikei` glued inside
a mostly romanised line, and `Landmine-Type` translated literally. The owner's note on it is that it
"has an understandable meaning that could be translated". It names a fashion and personality
subculture, doll-like and emotionally volatile, and English-language fandom writes both `jirai kei`
and `landmine girl`, so any of the three is defensible on its own and no two of them are defensible
together. Whichever policy is chosen above has to name what happens to a subculture term, or this
recurs under a different word.

### Romanise a name, translate a phrase

`重しれー女` ships as `Omoshiree Onna`, a bare romanisation. The owner's ruling: it "admits a
translation in the ordinary sense". おもしれー女 is a stock line rather than anybody's name, and 重
stands in for 面 to pun on 重い, a heavy or clinging affection. A rendering that romanises a phrase
tells an English reader nothing, and this is the same decision as A one step further on: an
honorific and a stock phrase are both language rather than name.

Whoever applies A should apply it in one pass over all 342 with the rule written into `facts/`, so
that it stops being decided per title, which is how it came to be decided both ways.

## Titles the owner raised on 2026-08-10 and which are not yet done

Each is confirmed and none is a policy question.

- **深爪さん is rendered two ways.** `Fukazume-san` on `ネイルちゃんと深爪さん。` and on its series
  row, `Cut-Too-Short-san` on the anthology. One person, one spelling; the pun belongs in the note.
- **`Café Hitoku-i` has a hyphen with no source.** The analyser split 秘匿異 into 秘匿 and 異 and the
  romaniser hyphenated across the split. It is キッサヒトクイ, which puns on 人喰い, a title this
  corpus also holds.
- **`伽藍の姫 -がらんのひめ-` romanises its own furigana gloss**, giving
  `Garan no Hime - Garan no Hime -`. The dashes carry the publisher's stated reading, not more title.
  "Princess of Cathedral" appears only on a scanlation aggregator, which is never an attribution.
- **お姉さまと巨人 has a licensed English name and the record does not hold it.** Yen Press publish it
  as *Sister and Giant: A Young Lady Is Reborn in Another World*. The `～` variant carries only our
  translation, so the licensed name wins there on rank; the `:` variant carries the Japanese
  publisher's own `MY SISTER AND GIANT`, which outranks a licensor's under the standing ruling.
- **Two romanisations reach a reader where they should not**, `Senketsu Ōjo, Minagorosu ~ ...` and
  `Watashi no Megami ga Kyō mo Oseru`, the second on a work that has an English name.

- **†でぃすてにぃ・ふれんず† prints its own English.** The work's lead page on カドコミ shows
  `Destiny` in Latin letters, read there by the owner on 2026-08-10. The record carried
  `†Disteny Friends†`, a misspelling invented here to mirror the hiragana affectation. How a work
  styles itself is the work's to decide and it had already decided. Corrected in
  `data/names/curated.yaml`; the apply was racing three agents writing the same files, so it is
  recorded here until a clean run lands it.

## A word the record itself says it could not resolve. Found 2026-08-10

Five renderings the owner corrected on one day were the same fault: **the source already stated the
answer and the pipeline reached past it for a guess.** The publisher's tagline said 勇者 while the
reading said ユウモノ. The title's own dashes said がらんのひめ and were romanised as more title. The
work's lead art said Destiny while the record carried a misspelling invented here. A note said 언니
while the rendering said Onni. And ベーズ, in a maid romance, is baize.

**The records flag it themselves.** Twelve curated entries carry a note saying, in their own words,
that a word could not be resolved: "does not resolve to any word or name found elsewhere", "isn't
glossed anywhere reachable", "kept in transliteration rather than guessed". That is a queue and not
a state, and nobody has worked it.

Resolved so far: `散り損ないのヒラエス` is Hiraeth, `ベーズのドアの向こうには` is baize, and
`ブリリアント・ブラウン` is recorded as a name whose own spelling has not been found.

Left, with the note's own admission beside each:

| Title | Rendering | What the note says |
|---|---|---|
| `メイドのデューデ` | The Maid's Dyūde | kept rather than guessed |
| `チャンマスと勇者ちゃん` | Chanmasu and the Hero Girl | does not resolve |
| `まるせっせんす` | Marusessensu | kept in transliteration |
| `ぐがぐもぐるてん` | Gugagumoguruten | does not resolve |
| `ことのことのは` | Koto no Kotonoha | kept in transliteration |
| `色知らぬ黒は青に触れる` | Black That Knows No Colour Touches Blue | rather than guess |
| `私の宝箱` | My Treasure Box | rather than guess |
| `御羊ちゃんは触りたい` | Little Miss Sheep Wants to Touch | rather than guess |

**One candidate worth checking rather than asserting**: `まるせっせんす` in hiragana reads as
*marcescence*, the botanical word for leaves that wither and stay on the branch through winter. That
is the same shape as ヒラエス for hiraeth, and it is a guess until a page says so.

**The setting is usually the evidence.** ベーズ was unresolvable in a record whose own note said the
work is a maid romance, which is the one setting where that word is a door. Whoever works this queue
should read what the entry already knows before looking anywhere else.
