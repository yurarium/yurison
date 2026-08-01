# Remaining gaps and the path through each

State as of 2026-08-01, after onboarding ニコニコ漫画. Written to be acted on, so each entry says
what the gap actually is, what the route through it costs, and what would make it worth doing.

Acceptance against both Tier C yardsticks now stands at 100% on watched platforms (202/202 against
Web漫画アンテナ excluding two deliberate 試し読み exclusions, 70/70 against 百合ナビ), across 705
releases and 316 works. Coverage is no longer the constraint. What follows mostly is not about
coverage.

---

## 1. Classification — the only gap that matters

**302 works, none with a `content_tier`.** Every work carries a `marketing_label`; not one carries
the interpretive axis. The two-axis scheme in [DEFINITIONS §3](DEFINITIONS.md) is currently
one-axis in practice.

This cannot be automated, and the temptation to try should be named so it can be refused: a
publisher's 百合 tag is `marketing_label` *by definition*, an aggregator's tag is a third party's
opinion, and "serialised in 百合姫" is the venue's identity rather than the work's. Deriving
`content_tier` from any of them would collapse the two axes into one and destroy the thing the
scheme exists to preserve.

**Path.** `adapters/classify/queue.py` builds `data/queue/classification.yaml`: every unclassified
work with its imprint, creator, volume count, first publication, and whatever platform and
aggregator tags we hold, plus an empty `content_tier` and a `basis` skeleton. Filling a row and
moving it to `data/overlay/<work_id>.yaml` classifies the work — the build already prefers overlay
over every source.

Ordered weakest-evidence-first, longest series first within each band, because that is where a
human adds most:

| Corroboration beyond the imprint | Works |
|---|---|
| none | 220 |
| one source | 48 |
| two sources | 34 |

**Cost.** Human, per work, and irreducible. But the queue is the difference between 302 blank
fields and 302 questions with the evidence already attached.

---

## 2. pixivコミック — reachable, deliberately not taken

Previously recorded as closed by operator choice. That was half right. The API at
`/api/app/works/...` returns 403 to a self-identifying non-browser request, and spoofing the client
to get past it is out under §5. But the site renders fine in an actual browser, and a browser is
the client the operator serves — no access control is circumvented by using one.

Confirmed 2026-08-01 by rendering `comic.pixiv.net/works/12066`: title, author, the publisher's own
百合 tag, per-episode availability (`掲載期間が終了しました` vs readable), and `更新日` at work
level. Everything needed is there.

**Path.** A rendering step in the pipeline, one page per work, ~131 works.

**Why not now.** Overlap 0.77 — the highest of any platform, meaning almost everything it lists is
available elsewhere too, usually at better image quality. Onboarding origin platforms erodes its
exclusive count without touching it, twice demonstrated. Adding a headless browser to the pipeline
is the largest single increase in operational complexity available, in exchange for the smallest
unique contribution of any large target.

**Trigger to revisit.** Re-measure its exclusive count now that ニコニコ is watched. If it stays
above ~40 works after that, the browser step earns its keep.

---

## 3. The unwatched long tail — 74 platforms, 269 exclusive works

**The previous entry here was wrong, and wrong in a way worth recording.** It said the long tail
offered "no leverage" and recommended leaving it alone. That came from probing six hosts, chosen
because they were the largest, for two engines. None of the six happened to be GigaViewer, and I
generalised from that to seventy-four.

`adapters/recon/probe.py` now surveys every unwatched platform for robots rules, feed endpoints at
the conventional paths, sitemaps, and the payload shape of one representative work page. Results in
`data/coverage/recon.yaml`.

| Cheapest route found | Hosts | Exclusive works |
|---|---|---|
| `server-rendered-page` | 30 | 112 |
| `page-no-date` | 9 | 64 |
| `unreachable` | 12 | 35 |
| `feed` | 15 | 35 |
| `sitemap-only` | 5 | 13 |
| `page-with-date-thin` | 3 | 10 |

### Already taken: 12 more GigaViewer platforms

Fifteen hosts serve a real feed, and twelve of them are GigaViewer instances that were sitting
there the whole time — FEEL web, ちゃおプラス, COMICリュウ, COMIC Y-OURS, まんがタイムSquare,
コミックボーダー, Seasons, 路草, パイコミックス, OUR FEEL, 栞, マガジンデビュー. They needed no code,
only registry rows, because one adapter has always served all of them. Watched platforms 13 → 22.

They contribute nothing *yet*, and that is expected rather than a failure: these are small sites
whose `/atom` holds about five entries, so a given yuri work appears only in the window where it
actually updates. FEEL web's feed at the time of writing carried two works, neither of them ours.
The adapter retains history across runs, so coverage accrues by polling rather than by backfill.

### Caveat that changes how the table should be read

`has_date` in the survey means "a date appears on the page", not "an update date appears".
ガンガンONLINE is the worked example: it is server-rendered and shows `2024.05.24発売！` — a
**単行本 release date**. Its chapter list loads client-side, so its real route is a rendered page,
not a fetch. Every `server-rendered-page` verdict therefore needs a second pass distinguishing an
update date from a volume date before an adapter is written against it.

### Routes for the remainder, by family

- **`jsonld` (7 hosts, 11 works)** — schema.org is standardised, so one parser serves all seven:
  ダ・ヴィンチニュース, コミックエッセイ劇場, 路草, アルファポリス, COMIC熱帯, マイナビニュース, plus
  two 更新終了 sites needing nothing. The generic-parser case, and the next thing to build.
- **`nuxt` / `next` (5 hosts, 25 works)** — マガポケ, ちゃおプラス, ヤンジャン+, ガンガンONLINE,
  コロナEX. Payload location differs per host but the extraction is the same shape as the カドコミ
  and FUZ adapters. ガンガンONLINE's payload is a 3.7 KB shell, so it belongs with pixiv under
  "needs rendering".
- **`markup` (21 hosts, 83 works)** — comicブースト 15, Gコミ 11, マンガPark 9, きら星ポータル 8,
  フラコミlike! 5, 少年ジャンプルーキー 4, 花とゆめ+ 4, and a tail of ones and twos. No shared
  engine, but the *code* is shared: one adapter driven by a per-host selector registry, which is
  a row of configuration per host rather than a program each.
- **`sitemap-only` (5 hosts, 13 works)** — enumeration works, dates do not. `<lastmod>` is a
  candidate signal but describes the URL, not the chapter; usable only if it can be corroborated.
- **`unreachable` (12 hosts, 35 works)** — of which several are marked 更新終了 by the antenna and
  need nothing at all. The live remainder are timeouts and 403s to be retried before conclusions.

### What this does not settle

269 works is the count of works these platforms carry that no watched platform carries. It is not
269 works of *unmet demand*: acceptance against both yardsticks is already at 100%, so nothing here
is currently being asked for and missed. The case for this work is completeness against a
definition the project has not yet written down, which is worth doing and worth being honest about.

## 4. Serialisation history

`first_publication` is the first 単行本 for every work in the catalogue, never the magazine
appearance — each record says so rather than implying otherwise. For a database whose scope is
"first published in Japan", the actual first publication is the serialisation.

MADB's magazine route was measured and abandoned: 9.3% coverage of contents overall and **zero**
for 百合姫, which is the lineage this catalogue is built on. `metadata108`, the undocumented
issue-contents relation, is the only remaining lead inside MADB.

**Path, in order of promise:**

1. 一迅社's own 百合姫 back-issue indices — the publisher lists contents per issue.
2. `metadata108` joined against cm102 issues for the 百合姫 magazine ids.
3. NDL's periodical holdings, which are per-issue rather than per-article and so probably too
   coarse.

**Cost.** Moderate for (1), unknown for (2). Worth doing before doujinshi.

---

## 5. Conflated title/author — 13 remaining

百合ナビ's WEB連載 cells run title and author together. 40 of 53 split against titles we hold; 13
remain, flagged 作者未分離 rather than split on a guess.

**Path.** Each needs one confirmed title from the platform that carries it. Two mechanisms now
exist and both are cheap: カドコミ author pages (`/search/author/<uuid>`) embed a creator's full
work list with codes, and ニコニコ漫画 states its works as `タイトル / 作者` directly. Between
them and comic-fuz.com search, the 13 are a short afternoon.

---

## 6. Doujinshi — Phase 4, not started

Deliberately deferred at the outset. Nothing has changed to bring it forward, and the pornography
exclusion in [DEFINITIONS §2](DEFINITIONS.md) needs settling before rather than during.

---

## 7. Smaller, known

- **openBD enrichment 252/646 volumes (39%).** Older ISBNs are simply absent from openBD; not
  fixable from this end.
- **Access data is sparse.** Only COMIC FUZ, the comici platforms and ヤンマガWeb state per-chapter
  access. カドコミ falls back to a platform-wide default recorded as the project owner's knowledge,
  not as a field read from the site.
- **百合ナビ 発売日 calendar** sits captured in `data/unwired/`, wired to nothing. It is the
  natural source for a 単行本 release feed, which the catalogue tab does not currently have.
