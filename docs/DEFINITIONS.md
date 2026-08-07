# Definitions

What this database counts as a yuri work, and how each record's classification is justified.

This document defines *inclusion*. [REQUIREMENTS.md](REQUIREMENTS.md) defines how records are
sourced, built and published.

---

## 1. The problem this document solves

"Yuri" (百合) is not one concept. At least three incompatible senses are in active use:

1. **A marketing label** — what a Japanese publisher prints on the work. Ichijinsha uses 百合;
   many publishers use GL / ガールズラブ; many works readers consider yuri carry no label at all.
2. **A content descriptor** — the work depicts romantic or sexual relationships between female
   characters, regardless of how it was sold.
3. **A fan tag** — whatever readers have tagged 百合 on aggregator sites.

These produce very different databases. The genre's own history compounds this: the term 百合
dates only to Itō Bungaku's column in *薔薇族* (1976), while the works treated as foundational are
older — 高橋真琴『さくらなみ木』(1957), 山岸凉子『白い部屋のふたり』(1971) — and the エス
(Class S) romantic-friendship tradition that precedes them is deliberately non-explicit.

**This database does not choose one sense.** It records the classification along two independent
axes, each with its evidence, so that a disputed call can be argued from the record rather than
taken on trust.

---

## 2. Inclusion test

A work gets a record if **any** of these is satisfied:

```
INCLUDE IF   content_tier ≠ incidental        (i.e. the relationship is central — see §3)
        OR   marketing_label ≠ none
        OR   a comparator lists it            (presumptive; see below)
```

subject to the scope rules (§6) and the exclusions (§7).

Works whose only qualification is `content_tier: incidental` and which carry no marketing label
are **recorded but excluded from default views**. They are retained because some are historically
notable, but they do not dominate the database.

**The comparators are a presumption, not a definition.** A work listed by 百合ナビ or Web漫画アンテナ
is taken as presumptively in scope without further argument. That is a claim about *coverage* — very
little of interest is absent from both — and not a claim that either site defines the genre. The
presumption is rebuttable: an attestation (§3) can place a work below the boundary, and the
exclusions in §7 override it outright.

**A licensed retailer's yuri shelf is a comparator.** Decided by the project owner on 2026-08-04.
A shop that stocks the publisher's edition and files it under its own 百合 genre is making an
editorial claim about scope, of the same kind as 百合ナビ making one, and it enters here on the same
terms: presumptive, rebuttable, and never a `marketing_label` (§4).

A retailer stands above an aggregator without becoming publisher-side. It sells the licensed
edition and answers for its own stock, so its filing is a matter of record instead of an opinion
about someone else's book. It is still the shop's classification and not the publisher's.

Record which comparator admitted a work, so a reader can tell whether it is here because a
publisher called it yuri or because a shop shelved it there. The shelves in use are
コミックシーモア genre 37 (百合・GL) and BOOK☆WALKER tag 14 (百合), measured in
[retailer-recon.md](../data/coverage/retailer-recon.md).

Two hazards come with them, both established by measurement rather than anticipated:

- **A shop shelves editions, not works.** The same work can sit on the yuri shelf in a censored
  edition and on the adult shelf uncensored. §7 governs, and governs the work.
- **A taxonomy that omits yuri is not a source without yuri.** コミックシーモア lists 27 top-level
  genres, gives one to BL and one to グリム童話 at 587 titles, and gives none to yuri at 1,869,
  which is reachable only from a work page. Absence of a category is not evidence of absent stock,
  and reconnaissance that reads only the advertised taxonomy will conclude otherwise.

The two axes are independent by design. `白い部屋のふたり` has canonical content and no label.
A thin *コミック百合姫* serial has the label and little content. Both belong, described accurately.

---

## 3. Axis 1 — `content_tier`

Interpretive, and **attested rather than adjudicated**. See
[RESEARCH-definition.md](RESEARCH-definition.md) for the sources behind this section.

### The boundary is centrality, not romance

Japanese usage does not run a ladder of romantic explicitness. It distinguishes a **broad sense
(広義)** — an intimate relationship between women, romantic or not — from a **narrow sense (狭義)**,
which is romantic and is used more or less interchangeably with **GL**. The broad sense is the
settled outcome of a definitional argument that has already run: the older formulation was about
female homosexuality and widened to strong relationships between women.

The editors of *コミック百合姫* describe the qualifying test as emotional weight and relational
depth, not romance, and decline to fix an edge at all — noting that their own creators disagree
about where it is. Two authors take the same line from different directions: 森島明子 makes 百合
observer-constituted rather than a property of the characters, and 仲谷鳰 explicitly includes
characters with no capacity for romantic feeling.

So the outer boundary of this database is:

> **a work primarily concerned with a close relationship between women, of any kind.**

*Of any kind* is meant literally — friendship, sisterhood, rivalry, mentorship, devotion. The
limiting words are **close** and **primarily concerned**: a work in which the relationship is
present but peripheral falls below the boundary and is `incidental`.

### Values

| Value | Criterion |
|---|---|
| `canonical-romance` | A romantic or sexual relationship between female characters is textually explicit — stated, depicted, or acted upon in the work itself. Not inference. |
| `strongly-implied` | The relationship is clearly romantic in framing and treatment but never stated outright. The reading is the obvious one, not one of several. |
| `class-s` | The エス tradition: intense, exclusive, romantically-coded female friendship presented within the conventions that treat it as a phase or an idealised bond rather than a relationship. Its own category, not a weaker `strongly-implied`. |
| `close-relationship` | The relationship is central and close but the work does not present it as romantic, and reading it as romantic would be an addition rather than an interpretation. The 広義 case. |
| `incidental` | Present but peripheral — a background couple, a single scene, a minor character. Below the boundary; excluded from default views when unaccompanied by a label. |

`class-s` is a *historical-conventional* judgment, not a strength judgment. Assigning it to a
post-2000 work requires justification in the `basis`.

`close-relationship` is the value this schema previously lacked, and its absence forced a
mis-coding either way: a work centrally about a non-romantic bond had to be called
`strongly-implied`, asserting romance it does not make, or `incidental`, denying a centrality it
plainly has.

**`canonical-romance` is not the same distinction as 狭義/GL.** Ours is an explicitness test — is it
in the text. The GL line is about whether romance is *settled*: GL presupposes a couple, while a
work can be unambiguously 百合 and leave the question open on purpose. Where a source draws the GL
line rather than ours, record what it said and do not translate it.

### It is a list, not a value

A tier is **a claim someone makes**, so the field holds every claim we hold, each with its own
`basis` (§5):

- Sources may **disagree**, and disagreement is a finding about a contested work rather than a
  validation failure. This project already records conflict rather than discarding it
  ([Requirements](REQUIREMENTS.md), source tiers).
- An attestation **need not name a tier**. A source that says only "this is 百合" attests the outer
  boundary and nothing finer. Forcing it onto the ladder would reintroduce exactly the judgment
  this model removes.
- **Our own reading is an attestation like any other**, recorded as ours, and optional.
- **No attestation is a legitimate state.** It is not a gap to be filled before the work can be
  shown.

### Attestations carry a date because the category moved

*コミック百合姫* marketed unrelated work aggressively as 百合 in its early years to widen the
category, then reversed after around 2010 and returned to romance as its core. A 2007 attestation
and a 2024 one may therefore disagree without either being wrong.

The project owner independently reports a sense of a step change in volume and tenor around the
same date — **recorded as an impression, not evidence**, and testable against our own publication
dates rather than against memory.

## 4. Axis 2 — `marketing_label`

Objective and verifiable from publisher-side evidence.

| Value | Criterion |
|---|---|
| `yuri` | The publisher applies 百合 to the work — cover, obi, catalogue entry, imprint, or official site. |
| `gl` | The publisher applies GL / ガールズラブ. |
| `magazine` | No direct label, but the work was serialised in a magazine whose own identity is yuri (『コミック百合姫』『百合姫S』『百合姫Wildrose』『ガレット』, and predecessors — see [the lineage list](#appendix-serialisation-lineage)). |
| `none` | No publisher-side yuri signal. |

`magazine` is deliberately weaker than `yuri`/`gl`: it attributes the venue's identity to the work,
which is a defensible inference but an inference nonetheless.

**Only publisher- or platform-side labelling counts.** A third-party site filing a work under 百合
— an aggregator tag, a tracking site's category, a shop's genre shelf — is evidence toward
`content_tier`, never toward this axis. The whole value of `marketing_label` is that it records
what the publisher did, and it is worthless the moment other people's opinions are mixed into it.

A licensed retailer is covered by that sentence and is named in it deliberately, because the
temptation to treat a shop as publisher-side is real: it sells the publisher's edition, so its
stock is a matter of record. What it shelves that edition under is still its own decision. A work
admitted on a retailer's shelf (§2) carries `marketing_label: none` unless a publisher-side signal
is found separately, and `none` continues to mean what §4 says it means, which is nothing about
content.

The imprint a retailer reports is a different matter. An imprint is the publisher's own, so
コミックシーモア naming 百合姫コミックス on a work is publisher-side evidence that happens to have
reached us through a shop, and it counts here on its own merits.

### `marketing_label: none` means nothing about content

This axis records a **commercial decision**, and its absence is not random. Publishers withhold the
label for reasons that have nothing to do with what is on the page:

- **Audience targeting.** A seinen or shōnen venue does not label a work 百合 even when the
  relationship is the premise, because the label addresses a different readership than the one the
  magazine is sold to.
- **Publisher policy.** Some houses do not use the term at all, in any imprint.
- **Platform convention.** General web-manga platforms — 少年ジャンプ+ among them — apply no genre
  label of this kind to anything.

So `none` is evidence about marketing, never about content. Reading it as "not very yuri" inverts
the axis's meaning.

**The practical consequence is a bias, not a gap.** A database assembled label-first will
faithfully reproduce the catalogue of yuri-specialist publishers and systematically thin out
everything else — including large, well-known works. The skew tracks publisher type and target
audience, so it cannot be corrected by collecting more labelled works.

`content_tier` therefore carries most of the field, and the discovery routes in
[Requirements §1](REQUIREMENTS.md) that do not depend on labelling are a **counterweight to a known
bias**, not a supplement to an otherwise sound method.

---

## 5. Evidence (`basis`)

**Every value on both axes requires a `basis`.** A classification without one fails validation.

A `basis` records:

- `source` — the Japanese source, from the allowlist in [REQUIREMENTS.md](REQUIREMENTS.md)
- `url` and `retrieved` date
- `note` — **our own paraphrase** of what the source shows

`note` is a paraphrase, not a quotation. Publisher synopsis and review text is copyrighted; any
literal quote must be short, clearly attributed, and genuinely subordinate to our own text. See
the media policy in [REQUIREMENTS.md](REQUIREMENTS.md).

---

## 6. Scope

### Inclusion is determined by first publication, not authorship

**A work is in scope if its first publication venue was in Japan.** Author nationality is
irrelevant.

| Case | Result |
|---|---|
| Japanese author, Japanese magazine or platform | In |
| Korean or Chinese author, first serialised in a Japanese magazine or on a Japanese platform | **In** — first publication was Japanese |
| Korean webtoon later localised to a Japanese platform | **Out** — the Japanese release is a translation of a non-Japanese original |
| Simultaneous multi-territory release | Out if the Japanese edition is a translation; in if the Japanese text is the original |
| Doujinshi sold at a Japanese event or shop | In scope in principle — deferred to Phase 2 (§7) |

`first_publication` is therefore a **required field**, because it *is* the inclusion test. But read
what the test asks: it turns on WHERE, and the date is not part of it.

**A work that exists is recorded whether or not we can date it.** Decided by the project owner on
2026-08-05. The venue and country are required, because those answer the scope question. The date
is recorded where it can be attested and its absence is stated where it cannot, as
`first_publication.date_basis`, never as an empty field pretending nobody looked.

This is not a loosening; it is the rule saying what it always meant. The retailer corpus made the
difference visible: BOOK☆WALKER states no ISBN anywhere and a print edition date on 31.7% of
volumes, and the absence is meaningful rather than careless, because every volume without one is a
digital-only product with no print edition to date. コミックシーモア states a delivery date that
ran 128 months from the printing in the worst case. Refusing those works would have been the
database asserting that a work it can see does not exist, on the strength of a field neither shop
holds.

What must never happen is a date invented to fill the field. A shop's delivery date, a platform's
import stamp and a first-of-the-month standing in for a month-precision record are all facts about
somebody's catalogue rather than about the manga, and each has already produced a wrong answer
here. An undated work says it is undated.

It is also **permanent**. Once a work's publication has been attested, that fact stays in the
database even if every source that attested it stops carrying the work. Scope is judged on whether
a work *was* published in Japan, never on whether it is still listed, in print, or online. See
[REQUIREMENTS.md §4](REQUIREMENTS.md#4-archival-integrity--the-record-persists).

### Formats

**In scope:** commercially published print manga (単行本, magazine serialisations, anthologies,
one-shots) and web manga first published on Japanese platforms (pixivコミック, ニコニコ静画,
コミックウォーカー, ガンガンONLINE, publisher web magazines, and author-published serials on
pixiv or X).

**Out of scope for now:** light novels and prose, including the 吉屋信子 tradition. It is the
genre's acknowledged ancestry, but it is not manga. It may later be added as non-record
contextual notes; it will not be given work records.

**Deferred:** doujinshi — see §7.

### Works and releases are different things

The inclusion test above applies to **works**. Individual chapters and chapter-like items of an
ongoing web serial are **releases**, tracked beneath their work and never independently classified
or included. A one-shot in an anthology is a work; chapter 43 of a serial is a release. See
[REQUIREMENTS.md §5](REQUIREMENTS.md#5-release-tracking-web-manga).

### A 試し読み sample is not web publication

Platforms list some titles as "series" whose entire output is 試し読み — sample chapters promoting a
printed volume. These are **not web manga**, and the scope rule already says so: the work's first
publication is the tankōbon, and the web posting is advertising for it.

So the samples are not releases and do not belong in a release feed. Counting them would overstate
web publishing activity with material that is really a shopfront.

The work itself is unaffected — it is a print work and belongs in the catalogue on that basis. In
practice these samples are a **useful discovery route to print works**: of the two found on
一迅プラス on 2026-08-01, neither was yet in the catalogue, so the sample was the only signal that
the volume existed. They are recorded as print candidates rather than discarded.

A 試し読み *within* a genuinely serialised work is a different thing: it is one release among
others, typed `trial`, and does not change the work's status.

---

## 7. Exclusions

### Pornography — excluded outright

**Works marketed or intended as pornography receive no record.** Not a flagged tier, not a hidden
view — no record.

The test is mechanical, using Japanese publishing's own objective signals:

- the 成年コミックマーク on the volume
- an 18禁 / R-18 designation by publisher or platform
- publication under an adult imprint
- distribution restricted to adult channels

Any one of these excludes the work.

### The test is a designation, never a judgement

Decided by the project owner on 2026-08-05, when the retailer corpus made the question unavoidable.

Nothing here asks whether a work IS pornography. Every signal above is a fact printed on an object
or recorded by a shop, checkable by two people who disagree about the work itself. What follows
from that admits far more than a judgement would.

**Doujinshi is a publication mode, not a content classification.** Treating "is this doujin" as a
proxy for "is this pornography" is a category error. Most yuri doujinshi is R-18, so the
designation excludes most of it anyway; one carrying no designation is admissible on exactly the
same terms as a commercial work. Excluding the category wholesale would drop admissible works to
spare us a judgement we do not have to make.

**Age-gating at retail is evidence and is recorded.** `age_gated` takes `gated`, `open` or
`not-stocked`, per retailer. BOOK☆WALKER keeps R18 on a separate store and コミックシーモア files
アダルト as its own genre, so both answer it directly. It varies between shops, which is itself
informative, and it settles publishers whose output is adult-adjacent without anyone deciding what
a given book "really is".

**A work with no designation is admitted, not excluded.** Where the content is explicit it carries
`explicit_content`, and where a reader would reasonably not want it unannounced it is kept out of
default views, which §2 already does for `incidental`. Three dispositions rather than two is what
makes the line hold: excluding on suspicion would mean a rule reading "we thought it looked like
pornography", and that is the thing this section exists to avoid.

**A bibliographic record is not the work.** A title, a publisher and an ISBN may be held for
something no page of which would ever be shown. The cover rule already encodes this by refusing any
cover on an `explicit_content` record, and that distinction is what lets the corpus be honest about
what exists without hosting any of it.

The residue is small and real: a work no shop gates, carrying no mark, from a publisher whose other
output is adult. Nothing objective remains to appeal to, so it is admitted and flagged.

**The test binds the work, not the edition.** Added 2026-08-04, from a case the retailer survey
turned up. A pornographic work can be reissued with the genitalia erased, titled 【棒消し修正版】,
【白抜き修正版】 or 【全年齢版】, and that edition carries no 成年コミックマーク, no R-18
designation and no adult imprint, so it passes every signal above while its uncensored twin sits on
the same shop's adult shelf.

Where an edition exists whose counterpart meets any signal above, the work is excluded.

The best evidence for the pairing is the seller's own catalogue rather than the title string. On
コミックシーモア an author's page lists both editions of the same work, one filed アダルトマンガ and
one marked -全年齢版- filed 青年マンガ, which states the twin instead of leaving it to be inferred
from a phrase. Where that is available, use it.

**This is the one rule excluding a work that carries no signal of its own, so it is the narrowest.**
It requires the counterpart to be IDENTIFIED, as an author page identifies it by listing both
editions side by side. A censorship marker in a title is a lead to check and never a verdict alone:
加筆修正版 is an authorial revision and 完全版 a collected reissue, and a work whose sibling nobody
has found is admitted like any other.

### The middle band — included, flagged

Works with explicit content that are **not** marketed as pornography are included, with
`explicit_content: true`. That covers a fair number of 百合姫-line and seinen titles, and also the
adult anthologies a mainstream publisher runs on its own platform: 一迅プラス carries
セフレ沼から抜け出せないっ！百合えっちアンソロジー and its like, which are explicit and are not
pornography by the test above.

**No cover image is referenced** for such a record. That is implemented and checked.

**Linking to the work is fine**, decided by the project owner on 2026-08-03. An earlier version of
this section said outbound links must go to bibliographic and publisher pages and never to a
reading page. Two things are wrong with that, and both matter:

- It was never built. Every record links wherever its platform put it, and
  昨日シたのに覚えてないの？ 百合えっち短編集 has linked to a reading page throughout. A rule
  nobody implemented is a rule that was doing nothing except making the document untrue, which is
  the same failure as the withheld register (STANDING-INSTRUCTIONS §13).
- The reasoning behind it does not survive the platform argument. Every platform here is a
  commercial publisher's own web arm. A reader following a link to a serialisation on one meets
  that publisher's own presentation of its own title, gated however the publisher gates it. The
  danger the rule imagined, a reader landing unawares on explicit content, is a danger about
  WHERE something is published, and this database only carries one kind of where.

What still excludes a work is the test above: the 成年コミックマーク, an 18禁 or R-18 designation,
an adult imprint, or distribution restricted to adult channels. Explicit is not the same as
marketed as pornography, and this section exists to hold the two apart.

### Consequence for Phase 2

Most yuri doujinshi is R-18. Under the exclusion above, a doujinshi phase covers only all-ages and
non-explicit doujinshi — a minority of the field, and it requires an R-18 filter that runs
**before** any record reaches the repository. This is understood in advance; whether the remaining
slice justifies the phase is a decision for Phase 2, not now.

---

## Appendix: serialisation lineage

The magazine line that anchors `marketing_label: magazine`, and the corpus for Phase 1:

| Magazine | Publisher | From | MADB ID |
|---|---|---|---|
| 『百合姉妹』 | サン出版 | 2003–2004 | — *(absent from MADB)* |
| 『コミック百合姫（月刊Comic ZERO-SUM増刊）』 | 一迅社 | 2005-09-01 | C117556 |
| 『コミック百合姫S』 | 一迅社 | 2007 | C117558 |
| 『コミック百合姫』 | 一迅社 | 2008-03-01 | C117557 |
| 『つぼみ』 | 芳文社 | 2009-02-27 | C123168 |
| 『百合姫Wildrose』 | 一迅社 | — | — *(absent from MADB)* |
| 『ガレット』 | ガレット works | 2017– | — *(absent from MADB)* |

Verified against MADB release 1.2.18 on 2026-08-01. 『つぼみ』 was added as a result; three of the
seven are absent from MADB and need publisher sources. See [MADB.md](MADB.md).

To be extended with any further yuri-identified magazines a publisher-side sweep reveals.

**A magazine is a venue, and the issue question is declined.** A magazine that carries yuri is worth
recording as a place where yuri is published, and is a different kind of thing from a work: it has
issues rather than volumes and contributors rather than an author. コミック百合姫 needs no per-issue
question, because the designation is the magazine. まんがタイムきららＭＡＸ carries some yuri and
saying WHICH issues would mean reading the contents and judging them, which §9 says this database
does not do. So the magazine is recorded and the issue-level question is left unanswered rather than
answered badly. A magazine carried as though it were a work, with volumes and an author, is a
category error and belongs in neither place.

## 9. Rebuttal, and the margin where this database declines to decide

§2 admits a work a comparator lists and calls the admission presumptive and rebuttable. For most of
this project's life nothing could rebut it, so the word did no work. `data/rebuttals.yaml` is the
mechanism, and it is deliberately narrow.

**A rebuttal is a finding about sources, never about a work.** It records that no source supports
the designation, or that a better-placed source contradicts it. `アルバート家の令嬢は没落をご所望です`
was removed because カドコミ, the publisher's own platform, files it 女性 / ファンタジー with 異世界,
ラブコメ, 転生 and 悪役令嬢 and applies neither 百合 nor GL, while one retailer volume carried the
shelf tag. That is a disagreement between sources with a clear winner, and §4 already says which of
the two speaks for the publisher.

**A work examined and kept is recorded too.** Without it the same works are re-examined at every
capture, and the reasoning is lost each time. `upheld` carries them, with `borderline` where the
call was close, so a later reader knows the question was asked and answered.

### Where this stops

At the outer margin, deciding whether a work is yuri would mean reasoning about the gender or the
sexuality of its characters, or about what its author intended. **This database does not do that.**
Neither is quantifiable from a source, both would come down to the feeling of whoever happened to be
looking, and §7's rule that this is designation and never judgement is not a posture that can hold
for the easy cases and lapse for the hard ones. It is exactly at the margin that it has to hold.

So a work nothing settles stays, and stays on whatever designation a source gave it. `海鳥東月の
『でたらめ』な事情` is in although the relationship is not a romance, because nothing in the
definitions requires one. `鈴木りつ短編集 考幻学入門` is in as an anthology containing yuri, which is
a different thing from a yuri work and is admitted as one. `ピエタとトランジ` and
`あなたのためなら女にでも` are in and marked borderline, which is the whole of what can honestly be
said about them.

This costs precision and it is the cheaper of the two errors. A work wrongly present is visible,
citable and can be rebutted by anyone who looks. A work wrongly absent is invisible, and the reader
who needed it never learns it existed.

### Present, addressable, and out of the listing

That reasoning is about EXISTENCE and it does not settle DISPLAY. A doubtful entry sitting in the
default listing still reads as an ordinary one, and dilutes what a reader is being shown. So there
is a third state between kept and gone: the work stays, its identifier stays, its page stays and
answers, and it does not appear in a listing unless the reader asks for it.

`data/rebuttals.yaml` carries two dispositions and the interface keeps them apart, because they say
different things. **`out`** is a source disagreeing with a source, which §4 can settle: the
publisher's own platform declined a designation a shop applied. **`marginal`** is this database
declining to decide, which is the section above rather than a gap in it.

Neither is deletion, and nothing here removes a record. A reader following a published address still
arrives somewhere that tells them what is known, which is the commitment that makes the cheaper
error cheap.
