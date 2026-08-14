# What a reader meets, and what is wrong with it: a plan

Written 2026-08-14 from a crawl of the live site, conducted as a reader rather than as a check. It
covered both language modes, all three tabs, all 3,038 work pages, about 180 credit pages, 54
publisher pages, the archived month view and `status.html`, and cross-checked what was rendered
against the JSON served under `/kari/data/`.

**WHY A CRAWL FOUND WHAT 127 CHECKS AND 16 READER CHECKS DID NOT.** Every check in this project asks
a question somebody already thought to ask. A crawl asks the only question a reader asks, which is
whether the page in front of them makes sense, and it reaches the places no check has a name for:
the fifth row of a dropdown, a tooltip, the "coming soon" view, a sort applied in the other language.
Most of what follows is invisible to any existing measure and several of the items are one line of
code.

Items 1 and 4 were verified against the served data directly and are quoted with their counts. The
rest come from the crawl's own reading, and each says what was seen and how sure it is. Where an
item needs something established before it can be fixed, that is written as the investigation rather
than folded into a fix nobody has justified.

**WHAT WAS CLEAN, WHICH IS PART OF THE FINDING.** No question marks, mojibake, replacement
characters, `null`, `undefined` or `[object Object]` on any page, which is this morning's floor-map
fix holding across the whole site. Every one of 3,543 generated pages resolves and an unknown
identifier answers 404. No console error and no failed request anywhere. Japanese mode showed no
English leaking into it. Every control the crawl exercised does what it says.

---

## 1. A link whose label, tooltip and destination disagree

**WHAT A READER MEETS.** On the "coming soon" view, `?month=soon`, five rows carry a platform chip
reading `KADOKOMI` whose address is `manga.nicovideo.jp`. The tooltip agrees with the label and not
with the link: "read this instalment on KADOKOMI". The same row then reads `· also on KADOKOMI`.
Clicking the name of one platform opens another company's site.

**WHAT IS ESTABLISHED.** Seven works carry `stated_next.platform` of `カドコミ` beside a `url` on
`manga.nicovideo.jp`: w00183, w00014, w02337 and four more. The row takes its NAME from
`stated_next` and its ADDRESS from `url`, and nothing requires the two to agree. The main feed's 322
rows have none of these, so the fault belongs to this view.

**THE INVESTIGATION.** Which of the two fields is right about where the next instalment appears. A
platform stating that it will publish next is a claim about that platform, so `stated_next` is
probably the true one and `url` is the work's current home; if so the row should link to the
platform it names, and the absence of an address for it is the thing to fix. Settled by reading
what the capture that writes `stated_next` actually saw.

**WHAT WOULD CLOSE IT.** A row may not draw a name from one field and an address from another, and
a check can say so: no rendered link whose visible label names a platform the address does not
belong to. That is a rule about the pair rather than about either half, which is why neither half
looks wrong on its own.

---

## 2. Work pages that disagree with themselves about serialisation

**WHAT A READER MEETS.** 100 work pages show a serialisation row whose every data cell is empty: a
platform name, then nothing for chapters, reading or newest. Three of them show a whole WEB
SERIALISATION table while the page's own summary line says "collected volumes" and names no web
edition. `work/w01317/`, Yuzumori-san, is the clearest: the summary offers volumes only, the table
below shows an empty Niconico Manga row, the state badge reads "Unknown", and the updates feed
listed a Yuzumori-san chapter on Niconico Manga on 2026-08-13.

**WHAT IS ESTABLISHED.** Four surfaces answer the same question and give different answers. The
other two cases are `work/w01352/` and `work/w01502/`.

**THE INVESTIGATION.** Whether an empty row means "this platform carries the work and we have read
nothing from it" or "this platform row should not exist". Those want opposite fixes, and the answer
is in what put the row there: a source record with no chapters, or a join that invented one. Worth
doing on w01317 first, because the feed proves the work IS serialised there, so the empty row is
missing data rather than a phantom.

**WHAT WOULD CLOSE IT.** A page may not offer a section it has nothing to put in, and where the
data really is missing it should say so in words, as the neighbouring cells already do with "76 not
recorded". Absence is a state and this is the one place the site renders it as blankness.

---

## 3. `status.html` contradicts itself

**WHAT A READER MEETS.** Four separate faults on one page.

  IT COUNTS THE CORPUS TWICE AND DIFFERS. The opening sentence says the run read releases "into
  3039 works"; the statistics block below says "3038 works"; the tab strip on the main site says
  3038. The sentence is built from `run.json:series_rows` and everything else from the works list.

  FIVE SOURCES ARE MINUS ONE DAY OLD. The age column shows `-1` for comicfuz, gigaviewer, kadokomi,
  nicovideo, openbd and webpages, all captured 2026-08-15. The page stamps itself in UTC and the
  captures are dated in Japan time, while the site tells readers every date on it is Japan time.

  A RAW KEY SITS AMONG SENTENCES. One row of "what this run did" reads `17 known-work-match` where
  its neighbours read "Merged chapters that two sources described separately".

  A SOURCE NAME PARSES AS ENGLISH. "The oldest capture is reachable, 12 days old" is naming the
  `reachable` source, and reads as a statement about whether the capture can be reached.

**THE INVESTIGATION.** Only the first needs one: whether 3,039 and 3,038 are two different
populations that happen to share a label, or one population counted two ways. `series_rows` counts
rows and the works list counts works, and a work held twice would explain the difference exactly.
The other three are wording and a timezone.

**WHAT WOULD CLOSE IT.** The page reports on the run, so every number on it should come from the
same account of that run rather than from whichever file was nearest. §13 put that account in the
store, which makes this cheaper than it was.

---

## 4. An adapter's name shown to readers as a platform

**WHAT A READER MEETS.** `bylines` appears in the Platform column of seven work pages and as an
option in the Works tab's platform filter. Every other one of the 50 platform values is a brand a
reader could recognise.

**WHAT IS ESTABLISHED.** The seven are w00038, w00341, w00613, w00703, w00969, w00973 and w00993.
The correct name exists and is unused: the feed calls the same source "Mynavi News" and
`feed/meta.json` carries `マイナビニュース`.

**THE INVESTIGATION.** None needed for the name. What is worth asking is how a value that is an
adapter's filename reached a column of brands at all, because that path will carry the next one.

**WHAT WOULD CLOSE IT.** A platform value should be drawn from the platform register rather than
from whatever wrote the row, and a check that every platform a reader is shown appears in that
register would have caught this the day it arrived.

---

## 5. Japanese platform names left untranslated in English mode

**WHAT A READER MEETS.** `きららベース` on 18 rows of the updates feed, `きら星ポータル` on a feed
row, a work page and both filter dropdowns, and `comicブースト` on 13 work pages and a dropdown.

**WHAT IS ESTABLISHED.** `きららベース` already has an entry in the interface's platform map and is
rendered through a span that bypasses it. The other two are absent from the map, where the remaining
47 platform names are present.

**THE INVESTIGATION.** None. Two are a missing map entry and one is a rendering path.

**WHAT WOULD CLOSE IT.** The reader checks already hold a budget for names an English page spells
itself; a platform is a closed vocabulary rather than a name nobody has researched, so the right
shape is the one `every credit role has an English gloss` already uses: an invariant at zero over a
list somebody wrote down.

---

## 6. Romanisations that collapse a title into one unreadable word

**WHAT A READER MEETS.** Seventeen visible with the default settings, among them
`Furekkusukomikkusu` for FLEX COMIX, sitting in a publisher dropdown that a reader operates. That
publisher's own name is Latin. A reader who uses the supported preference control to put
romanisation first, which is one drag, meets 95 of the 3,038 titles as single-word blobs:
`Tekunopanikkuyunibaasu`, `Furendogaarufurendo`, `Ririizukonpurekkusu`.

**WHAT IS ESTABLISHED.** `Marusessensu` and `Rinto Shite Kyun` look the same and are correct, so the
fault is word division rather than romanisation.

**THE INVESTIGATION.** Whether a name already holding a Latin form should ever be romanised from its
kana. FLEX COMIX writes itself in Latin and the store holds that; the romaji path reaches the kana
anyway. That is one question. The second is what to do where no Latin form exists and the analyser
cannot divide the words, which is the same gap `renderings resting on a mechanical romanisation`
counts and cannot fall until somebody researches the name.

**WHAT WOULD CLOSE IT.** The first half is a preference order that prefers a name's own Latin
spelling over a romanisation of its reading. The second half is the naming work that budget exists
to measure, and it should not be hidden by improving the first.

---

## 7. Chapter labels romanised by a worse rule than titles

**WHAT A READER MEETS.** On the Works tab's "latest" line: 41 rows capitalise Japanese particles,
`Koe Ni Nosete Fanfaare`, where titles correctly lowercase them, `Uesugi Kun wa Onnanoko o
Yametai`. 17 lose the space after a bracket and 38 run digits into words. The worst single string is
on `work/w00038/`: `Kuizu Dai64Kai Datou Feezaa! 80Nendai No4Suto250ccSengoku Jidai Ni Honki No
Honda Ga Hanatta Shikaku`. One feed row spells the same phrase two ways on one line, as a title and
as a chapter label.

**WHAT IS ESTABLISHED.** Titles and chapter labels are romanised by different code, and the title
path is the better one.

**THE INVESTIGATION.** Whether the title path can simply be used for both, or whether a chapter
label legitimately needs different handling. A chapter label carries counters and bracketed notation
a title does not, so this is not obviously a matter of deleting one path.

**WHAT WOULD CLOSE IT.** One romanisation rule with one home, which is §3 applied to a fact the site
computes twice. The two spellings on one line is the same evidence `a person is spelled one way`
rests on, one level down.

---

## 8. Copy and controls

**WHAT A READER MEETS.**

  A BILINGUAL MESSAGE IN A MONOLINGUAL MODE. Searching for something with no matches gives
  `該当なし / no matches` whatever the language is set to. Four copies of it are hardcoded in
  `index.html` with no marker for the splitter to find.

  A SORT THAT LOOKS BROKEN. Works tab, sort by title, English mode: the order is meaningless to an
  English reader because it is sorting the Japanese titles. The same positions in Japanese mode are
  correctly ordered.

  A COUNT THAT IS NEVER PLURAL. "1 recorded spellings" appears ten times on one publisher page and
  on 21 of the 27 sampled. The Japanese form beside it is correct.

  A STATE BADGE THAT STAYS JAPANESE IN BOTH MODE. On a work page in 両 mode everything is paired
  except the state chip, which renders `更新中` with an English tooltip. The works LIST pairs the
  same badge correctly.

**THE INVESTIGATION.** None for any of them.

---

## 9. Renderings with stray or doubled matter

**WHAT A READER MEETS.** 63 volume rows carry spaces around punctuation, `Gokigen'you , Ikkyoku
Ikaga ? vol. 4`, and the clean form already exists in the data and is discarded: that title holds
`Gokigenyō, Ikkyoku Ikaga?` as its English. Three feed rows say a platform is "also on" itself under
two spellings, `COMIC OGYAAA!! · also on Comic Ogyaaa!!`, because the store holds the same platform
under two names. Eight release rows print the publisher twice. Seven of 322 feed rows have a title
that is not a link, which the site's own budget already counts as "updates naming a work we do not
hold".

**THE INVESTIGATION.** For the doubled platform, whether `COMIC OGYAAA!!` and `コミックオギャー!!`
are one platform in the register or two, which is the same identity question the corpus answers for
works and people and has not been asked for platforms.

---

## 10. Blank where a word belongs

**WHAT A READER MEETS.** 568 of 1,820 serialisation rows have an empty "newest" cell, 470 of them
Niconico Manga and 98 KADOKOMI, while the cell beside them says "76 not recorded".

**THE INVESTIGATION.** Whether the date is genuinely unknown for those platforms or is being lost on
the way to the page. The concentration in two platforms suggests the former, and if so this is item
2's problem in a smaller frame: the site renders an unknown as blankness in the one place it has
words for it everywhere else.

---

## 11. One work under two English names

**WHAT A READER MEETS.** The updates and works tabs call a work "My Boyfriend's Girl Friend Keeps
Coming On Strong (At Me)"; the releases tab calls the same work
`Kareshi no Onnatomodachi ga Guigui Kuru Watashi ni`.

Two spellings of the Japanese title differ only in their brackets, `(私に)` against `〈私に〉`, and
only one carries a translation. `status.json` counts three works in this state and has done for some
time.

**THE INVESTIGATION.** Whether the bracket forms should fold together in the name key. They fold for
the work identity and not for the name map, which is a difference the two folds were designed to
have, so this is a question about which fold the releases tab should be joining on.

---

## What the crawl could not resolve

These are recorded as questions rather than as faults, because a guess presented as a finding is
worse than an open item.

  `[?]` SUPERSCRIPTS INSIDE TITLES look like leaked machinery and are documented as a deliberate
  mark for a reading nobody has confirmed, with a tooltip that says so.

  THREE ROMANISATIONS LOOK WRONG AND COULD NOT BE SETTLED: `Re岳` rendered `Retake`, `栖鴉` rendered
  `Sumika Karasu`, `フェザー` rendered `Feezaa`.

  THE "COMING SOON" VIEW lists rows dated before today tagged "Overdue", which may well be the point.

  A RELEASE DATED 2026-08-15 sits at the top of a feed whose own window declares it ends 08-14,
  which is consistent with Japan time and worth confirming rather than assuming.

## Smaller blemishes, recorded so they are not rediscovered

A blank Years cell on 7 of 27 sampled publisher pages. The en-US spelling toggle missing eight
titles whose British spellings are absent from its list, `Caramelisation` and `Romanticise` among
them, while the toggle itself works. Both platform dropdowns ordered by the Japanese name, so their
English labels read as unsorted. A tooltip on about 210 works reading "complete in 1 volume(s)" with
a raw plural, in English only. Internal design commentary shipped in `index.html`, reachable only by
viewing source.

## Order

Item 1 first, because it is the only one that sends a reader somewhere false. Then 4 and 3, which
are machinery and arithmetic a reader can see and each is small. Then 5 and 8, which are a map entry
and four strings. Item 2 and item 10 are one investigation and should be taken together. Items 6 and
7 are the largest and rest on a naming question that predates this crawl, so they belong after the
rest rather than in front of it.
