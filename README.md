# Yurarium

A bibliographic database of Japanese yuri (百合) manga, covering commercial print volumes and
Japanese web serialisations. Built from Japanese sources and published as a static site.

## What this is

A catalogue rather than a reader. It records what was published, by whom, where and when. For
serialisations still running it also records which chapters have appeared, and on what terms each
can currently be read.

## Policies

**Japanese sources only.** A foreign aggregator may suggest a title worth investigating. It may not
supply any stored field.

**Nothing is deleted.** Publication is a historical fact. When a source drops a title or a platform
delists a work, the record stays and is marked accordingly.

**No content is hosted.** No manga, no cover images, no publisher synopses. The database holds
bibliographic facts and links to authorised sources.

## Scope

Works first published in Japan, judged by publication venue rather than author nationality.
Anything marketed or intended as pornography is excluded.

Yuri classification is recorded on two independent axes: what the work contains, and what the
publisher called it. Each carries its own cited evidence, so a disputed call can be argued from the
record instead of taken on trust.

## Documents

- [Definitions](docs/DEFINITIONS.md): what counts as a yuri work, and how a classification is
  justified
- [Requirements](docs/REQUIREMENTS.md): sourcing, copyright policy, archival rules, architecture
- [Standing instructions](docs/STANDING-INSTRUCTIONS.md): how the project is worked on, and what is
  enforced at check-in
- [Takedown policy](TAKEDOWN.md)

## Licence

- **Code, schema, adapters, documentation**: [MIT](LICENSE)
- **Original data contributions**: [CC0 1.0](DATA-LICENSE.md), covering classifications, evidence
  notes and dataset structure. Bibliographic facts are not copyrightable and are not licensed by
  anyone.
- **Third-party source data**: remains under its own terms and is **not** relicensed here. MADB
  requires attribution and version citation. openBD restricts use to book-introduction purposes and
  forbids transferring use rights. See [DATA-LICENSE.md](DATA-LICENSE.md).
