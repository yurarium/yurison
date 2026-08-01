# MADB: what it actually gives us

Findings from working the 文化庁メディア芸術データベース bulk datasets against the 百合姫 lineage,
2026-08-01, release 1.2.18.

The short version: MADB cannot supply the Phase 1 corpus. It is strong exactly where
[Requirements §7](REQUIREMENTS.md) put Phase 2, and thin where it put Phase 1.

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

## What this changes

MADB gives us magazine-level metadata for three of the five magazines in the 百合姫 lineage, partial
issue lists, and no contents. Building the Phase 1 corpus from it is not possible.

Two things follow.

**Phase 1 has to run on publisher sources.** 一迅社's own site and ichicomi carry the 百合姫 catalogue.
MADB stays in the picture for magazine-level facts and for 単行本 records once titles are known, but
it cannot enumerate the corpus.

**MADB is a Phase 2 asset, and a good one.** 花とゆめ, りぼん, なかよし and ガロ are covered at the
contents level across hundreds of issues each, and those are the magazines where Class S and the
pre-1990s precursors ran. The historical sweep that [Requirements §7](REQUIREMENTS.md) treats as the
harder, later problem is the part MADB makes tractable.

Whether to reorder the phases on that basis is open.

## Practical notes

- Pin the release tag per [Data licence §3](../DATA-LICENSE.md); MADB requires the dataset version be
  cited.
- `schema:publisher` is sometimes a string and sometimes a list. So are `schema:name` and
  `schema:creator`. Adapters must normalise before comparing.
- Publisher strings carry an embedded reading: `一迅社　∥　イチジンシャ`, split on `∥` with ideographic
  spaces. Some records give the bare name instead.
- Bulk data is cached outside the repo at `~/workspace/madb-cache/<tag>/` and is not committed.
