# The naming job

You are running unattended in GitHub Actions after a Yurarium update. Yurarium is a bibliographic
database of Japanese yuri manga. Read `CLAUDE.md` and `docs/STANDING-INSTRUCTIONS.md` first; they
outrank this file.

Your queue is `data/build/naming-queue.md`. It lists up to three kinds of work. Do what it lists and
nothing else, then stop. A person reviews the result afterwards and will say if anything should
change, so research each item properly rather than quickly.

## What you may change

The work registry `data/identity/works.yaml`, the English names and readings in
`data/names/curated.yaml`, and the inclusion rulings in `data/queue/unheld-works.yaml`. The workflow
rejects any other change and discards your work.

Do not edit code, budgets, documentation or any capture under `data/source`.

## Works awaiting an identifier

Each is a row the build compiled and could not key, so no reader can open it.

1. Open each address and confirm it is a manga work on that platform, by that creator.
2. Decide whether it belongs, under `docs/DEFINITIONS.md` §2. The owner's standing rules: a work
   on a known platform that does not gate readers by age is admitted by default, and a comparator
   listing (百合ナビ, Web漫画アンテナ's 百合 tag, a licensed shop's 百合 shelf) is an inclusion basis.
   §6 (scope, such as a work first published outside Japan) and §7 (adult markers) still exclude.
3. Before minting, search the registry for the same work under another record: the same title
   with the same creator, a print record (`madb:` anchors with `title: null` are common), or the
   same work on another platform. If it exists, add the address to that entry's `anchors` with an
   `attached` basis instead of minting. A print entry carries `title: null`, so searching the
   registry by title misses it: search `data/source` (the `bookwalker`, `madb` and `webpages`
   captures) for the title too, and find the entry by the record id it names.
4. Otherwise mint the next identifier after the highest `wNNNNN` in the file, appended at the end
   of `works:` and before `related:`. Give it `title` and `anchors` (`"web:<address>"`). For a
   GigaViewer chapter address (`/episode/<digits>`), read the page's own `atom/series/<id>` link
   and add that feed as a second anchor with an `attached` entry whose basis quotes the link and
   the og:title, dated today. Look at the entries for w03274 and w03321 for the shape.
5. If it does not belong, write a ruling instead (below) and mint nothing.
6. A work that already has a ruling in `data/queue/unheld-works.yaml` is not yours, whatever the
   ruling says: `held` means the owner is deciding it. The queue leaves such works out.

## Works the feed names with no record and no ruling

Add a ruling to `rulings:` in `data/queue/unheld-works.yaml`: `work`, `platform`, `platform_url`,
`disposition` (`in` or `out`), `admitted_under` for an `in`, and `why`, starting "Ruled <date>."
The ruling explains; it does not mint. Follow the entries already there.

## English names

Every work you mint, and every title listed under "Titles showing a romanisation", gets an entry
under `titles:` in `data/names/curated.yaml`, keyed by the Japanese title exactly as the row has it.
Search the file first: a key written twice refuses the whole apply.

Find an existing English name before translating, in this order, and cite the page:

- `official-jp`: an English title the work carries itself, on the platform page, its logo or
  title image, or its first content page. `source_kind` is `platform` or `publisher-jp`.
- `licensed`: an English edition's own title from its licensor's catalogue (Seven Seas, Yen Press,
  Kodansha USA and so on). `source_kind: licensor`, with `source_url`.

Where one exists, still add `translation` (and `translation_note` if the two differ in a way worth
saying): a reader can choose to see our rendering beside the publisher's.

Otherwise translate: `basis: translated`, `source: "yurarium"`, `source_kind: derived`. Read the
platform's synopsis and the first chapter's title before choosing, and say in `note` what the title
means and why you rendered it so, naming the page you read. Translate meaning, keep a deliberate
pun or coinage where English can carry it, and keep a title that is itself a coinage or a proper
name in romanisation (`basis: romaji`). A title written in katakana English is `translated`, spelled
as the English it borrows.

Every entry carries `reviewed:` with today's date in quotes. If you give a `reading`, it is
katakana with spaces between words, with `reading_basis` and `reading_source_kind`, and a
`reading_note`; a reading worked out here is `researched` and `derived`.

## Then check your work

    python3 adapters/names/curate.py --apply
    ./build.py
    ./check.py --gate

`curate.py` names any entry it rejects; fix it. The gate may already fail on budgets for reasons
that have nothing to do with you, and the workflow compares it with the gate before you started,
so do not edit budgets to make it pass. Fix only what your own entries caused.

## How to write

Notes are read by people. Plain sentences, no em dashes, keep Japanese quotation marks and curly
quotes as the source has them, and do not reach for lists of three. Say what a thing is, not what
it is not.

## Finish

End with a short summary: what you minted (id and title), what you named and on which basis, what
you ruled, and anything you could not settle and why.
