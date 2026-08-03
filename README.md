# Yurarium

A bibliographic database of Japanese yuri (百合) manga, covering commercial print volumes and
Japanese web serialisations. Built from Japanese sources and published as a static site.

## What this is

The database records what was published, by whom, where and when. For serialisations still
running it also tracks which chapters have appeared, and the terms on which each can be read
today. Every entry links out to the platform that carries the work.

## Policies

**Sources are Japanese.** A foreign aggregator may point at a title worth investigating. Every
stored field comes from a Japanese source.

**The record is permanent.** Publication is a historical fact. When a source drops a title or a
platform delists a work, the entry stays and gains a marker saying so.

**Only bibliographic facts are held.** Titles, creators, dates, venues, chapter listings, and links
to authorised sources. Cover images, synopses and manga stay with the publishers who own them.

**Pornography is out of scope.** Works marketed or intended as such are excluded.

## Scope

Inclusion follows the publication venue: a work first published in Japan qualifies whatever the
author's nationality.

Every work is classified on two independent axes, one for what it contains and one for what the
publisher called it. Each axis carries its own cited evidence, so a disputed call can
be argued from the record.

## Documents

- [Definitions](docs/DEFINITIONS.md): what counts as a yuri work, and how a classification is
  justified
- [Requirements](docs/REQUIREMENTS.md): sourcing, copyright policy, archival rules, architecture
- [Standing instructions](docs/STANDING-INSTRUCTIONS.md): how the project is worked on, and what is
  enforced at check-in
- [Takedown policy](TAKEDOWN.md)

## Licence

Code, schema, adapters and documentation are [MIT](LICENSE). Original data contributions are
[CC0 1.0](DATA-LICENSE.md), covering classifications, evidence notes and dataset structure.
Bibliographic facts are not copyrightable, and nobody licenses them.

Third-party source data keeps its own terms and is **not** relicensed here. MADB requires
attribution and version citation. openBD restricts use to book-introduction purposes and forbids
transferring use rights. See [DATA-LICENSE.md](DATA-LICENSE.md).
