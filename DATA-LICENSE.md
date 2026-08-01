# Data licence

Code, schema, adapters and documentation are MIT — see [LICENSE](LICENSE). This file covers the
**database records**, which are not a single thing with a single owner.

## 1. Bibliographic facts — not licensed, because they cannot be

Titles, creators, publishers, ISBNs, dates, volume counts, magazines and serialisation runs are
**facts**. Facts are not copyrightable (Japan Art. 10(2); *Feist v. Rural* in the US), so nobody —
including this project — holds rights over them, and no licence grant is needed or possible.

A database's *selection and arrangement* can attract thin protection as a データベースの著作物
(Japan Art. 12-2). To the extent any such right subsists in this compilation, it is waived under §2.

## 2. Original contributions — CC0 1.0 (public domain dedication)

To the extent that copyright or database rights subsist in them, the following are dedicated to the
public domain under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/):

- yuri classifications (`content_tier`, `marketing_label`) and their assignment to works
- evidence notes written for this project
- the selection, arrangement and structure of the compiled dataset
- record identifiers and cross-references originating here

Use them for anything, without permission or attribution. Attribution is welcomed, not required.

CC0 is the norm for library and bibliographic metadata, and it is the right fit: the value here is
in the work having been done, not in controlling what anyone does with it afterwards.

## 3. Third-party source data — **not relicensed by this project**

Records are assembled from Japanese sources that impose their own terms. **Those terms are not
ours to waive, and §2 does not attempt to.** Anyone redistributing data obtained from this project
remains bound by them.

| Source | Terms that travel with the data |
|---|---|
| [文化庁メディア芸術データベース](https://github.com/mediaarts-db/dataset) (MADB) | Free secondary use, but: note where data was edited or processed, retain the notice that it is openly reusable, respect creators and related communities, observe non-copyright rights, and cite the dataset version. Derived records here record the MADB version used. |
| [openBD](https://openbd.jp/) | Usable for book introduction and promotion purposes (本の紹介・販促) only. Data must not be arbitrarily modified. Deletion requests must be honoured promptly. **The right to use API-obtained information may not be lent, transferred or sold to third parties.** |
| [国立国会図書館サーチ](https://ndlsearch.ndl.go.jp/) (NDL) | Subject to NDL's own terms of use. |
| Publisher and platform pages | Facts extracted only; no publisher prose is stored. |

Two consequences that shape what this repository contains:

- **No bulk openBD dump is published**, as a standalone dataset or otherwise. Whether openBD's
  no-transfer clause reaches bulk republication is genuinely unclear, so the project does not test
  it. The site itself is a 紹介 interface, which is squarely within openBD's stated permission.
- **Source-supplied values are stored as fetched, in a layer separate from curation**, so that
  openBD's no-modification term is satisfied and corrections are never presented as openBD's data.
  See [Requirements §5](docs/REQUIREMENTS.md).

## 4. What is not here at all

No manga, no page images, no cover image files, no publisher synopses. Cover images are referenced
from publisher-supplied reuse feeds and served by those publishers, never stored here. See
[Requirements §2](docs/REQUIREMENTS.md) and [TAKEDOWN.md](TAKEDOWN.md).

---

*Not legal advice. If you intend to redistribute data obtained from this project, read the source
terms above rather than relying on this summary.*
