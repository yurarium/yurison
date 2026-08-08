# MADB: what it actually gives us

Findings from working the 文化庁メディア芸術データベース bulk datasets against the 百合姫 lineage,
2026-08-01, release 1.2.18.

The short version: magazine contents are unusable for our magazines, but the 単行本 imprint field
enumerates the whole Phase 1 corpus. 646 volumes, 302 works, all with ISBNs.

## Release cadence

MADB ships monthly. Latest is **1.2.18 (2026-07-17)**. Earlier notes in this repo assumed a stale
v1.2 from January 2024 and warned about currency; that was wrong. Worst-case lag is about a month.

Release assets are the current full datasets. The files under `data/json-ld/` on the main branch are
an older base, split into numbered parts, and are larger on disk without being more complete: cm105
holds 5,728 magazines there against 5,753 in release 1.2.18. Pull from Releases, pin the tag.

## Dataset numbering

The README table documents cm101–cm107. The release assets do not match it. `metadata108` and
`metadata109` exist, are large, and appear in no table:

| Asset | Records | Content |
|---|---|---|
| `metadata101` | — | マンガ単行本 (volumes) |
| `metadata102` | 179,908 | マンガ雑誌各号 (issues), `schema:isPartOf` → magazine |
| `metadata104` | 139,130 | マンガ単行本シリーズ |
| `metadata105` | 5,753 | マンガ雑誌 (magazines) |
| `metadata106` | 30,023 | マンガ雑誌掲載履歴 |
| **`metadata108`** | **453,705** | **`class:Supplement` — issue contents. Undocumented.** |
| `metadata109` | 1,069,967 | `class:Supplement`, holdings/copy records |

`metadata108` is the only place the work↔issue relation exists. Anyone reading the README alone will
not find it.

## The join

Four hops, and one field name actively misleads:

```
cm105 magazine (C…)
  ← schema:isPartOf ←  cm102 issue (M…)
  ← ma:relatedCollectionOfMagazine ←  cm108 Supplement (S…)
  → ma:relatedCollectionOfManga →  work (C…)
```

`ma:relatedCollectionOfMagazine` points at an **issue**, not a magazine. Filtering it against
magazine IDs returns nothing and looks like an empty result rather than a mistake.

cm106 (掲載履歴) carries no magazine reference at all. Its `ma:note` is free text about the work. It
cannot be joined to a magazine from the bulk data.

## Coverage of issue contents

cm108 covers **16,644 of 179,908 issues, or 9.3%**, concentrated on major mainstream titles:

| Issues with contents | Magazine |
|---|---|
| 2,889 | 週刊少年サンデー |
| 2,887 | 週刊少年マガジン |
| 2,343 | 週刊少年ジャンプ |
| 2,322 | 週刊少年チャンピオン |
| 1,054 | ビッグコミック |
| 849 | 花とゆめ |
| 806 | なかよし |
| 776 | りぼん |
| 555 | 週刊漫画アクション |
| 412 | 月刊漫画ガロ |

**The 百合姫 line has zero contents records.** So does つぼみ.

## The yuri magazines MADB does hold

Searching cm105 for 百合 returns four records, one of them unrelated:

| ID | Magazine | Publisher | First | Issues in cm102 |
|---|---|---|---|---|
| C117556 | コミック百合姫（月刊Comic ZERO-SUM増刊） | 一迅社 | 2005-09-01 | 9 |
| C117558 | コミック百合姫S | 一迅社 | 2007 | 16 |
| C117557 | コミック百合姫 | 一迅社 | 2008-03-01 | 44 |
| C121244 | 百合子 | 黒蘭社 | — | — |

`つぼみ` (芳文社, 2009-02-27, C123168) is present but holds no issues in cm102. It belongs in the
lineage and was missing from the appendix in [Definitions](DEFINITIONS.md).

Issue coverage is partial even where it exists. コミック百合姫 has run monthly since 2008 and should
have upwards of 200 issues; cm102 holds 44.

**Absent entirely:** 百合姉妹 (2003–2004, サン出版), 百合姫Wildrose, ガレット (2017–). For 百合姉妹
this is not a search artefact. All 35 サン出版 magazines in cm105 were listed and it is not among
them.

Records carry よみがな under `ja-hrkt`, which satisfies the transliteration requirement without a
separate romanisation step.

## The imprint route — this is how the corpus is built

Magazine contents are a dead end, but 単行本 are not. cm101 carries `schema:brand`, which holds the
レーベル, and the 百合姫 line is there.

Matching `schema:brand` against a normalised form of `Yurihime comics` / `コミック百合姫` /
`百合姫コミックス` / `百合姫books` yields **646 volumes across 302 works, 2006-02 to 2026-06-15, every
one with an ISBN.** That is the Phase 1 corpus, at the size §7 predicted, and the ISBNs give a direct
join to openBD.

MADB spells the imprint at least seven ways, including case and hyphenation variants and one that
drops the `IDコミックス` prefix entirely:

```
IDコミックス. Yurihime comics                 237
IDコミックス / Yuri-hime comics               163
IDコミックス / Yurihime comics                136
IDコミックス. コミック百合姫                     30
IDコミックス. Yurihime comics = コミック百合姫      8
Yuri-Hime COMICS                            …
百合姫books                                   1
```

Any exact match on this field loses most of the corpus silently. Normalise (NFKC, casefold, strip
separators) and match on substrings.

### What the separator means, measured

The notation carries no hierarchy of its own, and this was checked before it was relied on.
`schema:brand` is a list, and 一迅社's series records give the same pair of names as the list
`["IDコミックス", "Yurihime comics"]` on 87 records and as the single string
`IDコミックス　／　Yurihime comics` on 14. The order carries nothing either: the release holds
`Zero-sum comics　／　IDコミックス`, `REXコミックス　／　IDコミックス` and
`DNAメディアコミックス　／　IDコミックス` alongside the umbrella-first forms, and one record reads
`4コマkingsぱれっとcomics　／　4コマKINGSぱれっとCOMICS`, which is one name joined to its own case
variant. The separator itself changes with the cataloguing of the day: `Action comics : comic
high's brand` and `Action comics　／　comic high's brand` are the same 双葉社 line under two of them.

So the separator joins list values, the specific element is the identity, and the umbrella is a
fact about the line and not part of its name.

### The hyphen is the publisher's, and the case is not

The 百合姫 logotype loses its hyphen at books **published** in 2015: every volume dated 2014 is
`Yuri-hime`, 2015 splits 22 to 28, and nothing after 2016 is hyphenated. openBD turns over in the
same year. That is not a cataloguing sweep, and the record dates say so directly: MADB modified
every pre-2025 record of the line in one pass in 2024, and that pass emitted the hyphenated form 193
times and the bare form 378 times. The form came off the book.

`YH comics` is a different matter and runs alongside the spelt-out form every year from 2015, on the
volumes of the same series: C357075 carries `YH comics`, `Yuri-hime comics`, `Yurihime comics` and
`yh comics` across its own run, and one series carries `Yuri-hime comics` beside `百合姫コミックス`.
Same line, four transcriptions.

**`YH comics` is missing from `extract.IMPRINTS`,** which is a live fault rather than a note. 36
一迅社 series records in release 1.2.18 state it, 30 of them are in this corpus, and each was stored
as `imprint: IDコミックス` with `marketing_label: none` because the selection never matched. They
entered on a retailer's shelf instead, so the publisher-side label they are entitled to is missing.
Adding the spelling is one line; landing it needs a re-extraction, and `labels with nothing to
quote` would then rise from 0 to about 30 because `YURI_TERM_IN_IMPRINT` does not recognise `YH`
either. That budget reading 0 today is partly this fault hiding inside it: the works that would be
counted never got the label that would put them in the count.

The imprint is publisher-side labelling, so it establishes `marketing_label: yuri` mechanically
under [Definitions §4](DEFINITIONS.md), with the brand field as its basis. The interpretive axis
still needs a human.

### Grouping traps

**About a third of volumes carry no `schema:isPartOf`.** 197 of 646. These are recent records
ingested from NDL that MADB has not yet resolved to a series. Grouping on the series link alone
drops them. The extractor falls back to normalised-title matching and records which route produced
each work:

| Route | Works |
|---|---|
| `series-link` | 222 |
| `mixed` | 12 |
| `title-match` | 15 |
| `title-only` | 53 |

**Volumes of one work can sit on both sides.** 半熟女子 vol 1 (`Yuri-Hime COMICS`, no series link)
and vol 2 (`IDコミックス / Yuri-hime comics`, linked to C357308) are the same work. Series-link
grouping alone produces a one-volume work numbered "2", which looks plausible and is wrong.

**MADB holds duplicate series records.** ゆるゆり appears as two works, 26 volumes and 12. Merging
them is a curation decision and belongs in the overlay, not the adapter — the source layer reports
what MADB says.

## What this changes

**Phase 1 runs from MADB after all**, via the imprint rather than magazine contents. Publisher
sources are still needed for the magazines MADB lacks and for serialisation-level detail, but the
corpus enumerates from bulk data.

**Phase 2 may be easier than assumed.** 花とゆめ, りぼん, なかよし and ガロ are covered at contents
level across hundreds of issues each, and those are where Class S and the pre-1990s precursors ran.
The historical sweep [Requirements §7](REQUIREMENTS.md) treats as the harder, later problem is the
part bulk data supports best. Whether to reorder is open.

## Note on platform onboarding

The 302-work catalogue is also the identification set for web platforms that apply no genre labels.
See [Requirements §5](REQUIREMENTS.md); the short version is that its narrowness is currently the
binding constraint on release coverage.

## Practical notes

- Pin the release tag per [Data licence §3](../DATA-LICENSE.md); MADB requires the dataset version be
  cited.
- `schema:publisher` is sometimes a string and sometimes a list. So are `schema:name` and
  `schema:creator`. Adapters must normalise before comparing.
- Publisher strings carry an embedded reading: `一迅社　∥　イチジンシャ`, split on `∥` with ideographic
  spaces. Some records give the bare name instead.
- Bulk data is cached outside the repo at `$YURI_CACHE/madb-cache/<tag>/` and is not committed.
