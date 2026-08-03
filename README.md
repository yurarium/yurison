# Yurily

A bibliographic database of Japanese yuri (百合) manga — print and web, historical and current —
built from Japanese sources and published as a static site.

**Status: running.** 1,366 tracked releases across 22 platforms, 1,009 web works, 302 print works.
The site updates from the platforms' own feeds. Current coverage, source freshness and outstanding
work are reported on the site's own technical view rather than restated here.

## What this is

A catalogue, not a reader. It records what was published, by whom, where and when — and for
ongoing web serialisations, what has been released and on what terms it can currently be read.

Three commitments shape everything else:

- **Japanese sources only.** Foreign aggregators may suggest a title to investigate. They may not
  supply a single stored field.
- **Nothing is ever deleted.** A work's publication is a historical fact. Sources drop titles,
  platforms delist works, magazines fold — the record persists regardless, marked rather than
  removed.
- **No content is hosted.** No manga, no cover files, no publisher synopses. Bibliographic facts
  and links to authorised sources, nothing more.

## What it covers

Works first published in Japan — judged by publication venue, not author nationality. Commercial
print manga and Japanese web manga. Works marketed or intended as pornography are excluded
outright.

Yuri classification is recorded on two independent axes — what the work contains, and what the
publisher called it — each with its evidence cited, so a disputed call can be argued from the
record rather than taken on trust.

## Documents

- [Definitions](docs/DEFINITIONS.md) — what counts as a yuri work, and how each record's
  classification is justified
- [Requirements](docs/REQUIREMENTS.md) — sourcing, copyright policy, archival rules, architecture
- [Standing instructions](docs/STANDING-INSTRUCTIONS.md) — how the project is worked on, and what
  is enforced at check-in
- [Takedown policy](TAKEDOWN.md)

## Licence

- **Code, schema, adapters, documentation** — [MIT](LICENSE)
- **Original data contributions** — [CC0 1.0](DATA-LICENSE.md) (classifications, evidence notes,
  dataset structure). Bibliographic facts are not copyrightable and are not licensed by anyone.
- **Third-party source data** — remains under its own terms and is **not** relicensed here; MADB
  requires attribution and version citation, openBD restricts use to book-introduction purposes and
  forbids transferring use rights. See [DATA-LICENSE.md](DATA-LICENSE.md).
