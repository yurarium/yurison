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
— an aggregator tag, a tracking site's category — is evidence toward `content_tier`, never toward
this axis. The whole value of `marketing_label` is that it records what the publisher did, and it
is worthless the moment other people's opinions are mixed into it.

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

`first_publication` (venue, date, country) is therefore a **required field**, because it *is* the
inclusion test.

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
