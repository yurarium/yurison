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

## 3. The unwatched long tail — worked through

**The entry that stood here twice was wrong.** First it said the tail offered no leverage, from
six hosts probed for two engines. Then it said the survey had found the leverage, from a heuristic
that could not tell a chapter date from a 単行本 release date. Both were conclusions drawn from
samples that decided the answer in advance.

All 74 platforms have now been surveyed twice — once for shape (`adapters/recon/probe.py`), once by
attempting the extraction itself (`adapters/recon/extract.py`) — and every one has a disposition.

| Disposition | Hosts | Exclusive works |
|---|---|---|
| solved — GigaViewer feed | 15 | 47 |
| solved — generic extractor | 8 | 26 |
| solved — comici pages | 5 | 19 |
| dead — 更新終了, needs nothing | 14 | 31 |
| blocked — 403/412/host down | 7 | 18 |
| open — needs rendering | 25 | 128 |

**123 of the 269 works are now reached or need nothing.** Attested releases went 478 → 553 over the
course of this work.

### Solved, and how

- **GigaViewer (15)** — twelve instances were sitting unnoticed. Registry rows, no code.
  comicブースト (15), FEEL web (7), ちゃおプラス (5), COMICリュウ (5), COMIC Y-OURS (4), まんがタイムSquare (2), コミックボーダー (2), Seasons (2), 路草 (1), マガジンデビュー(更新終了) (1), パイコミックス (1), OUR FEEL (1), 栞 (1)
- **comici (5)** — four more installs of the engine ビッコミ and 竹コミ already use, found by
  trying the extraction rather than grepping five homepages for a marker.
  Gコミ (11), 花とゆめ+ (4), ライコミ (3), COMICリュエル (1)
- **generic extractor (8)** — `adapters/generic/releases.py`. The 21 markup-only hosts have no
  engine in common but share the *shape* of a chapter list: repeated blocks each carrying a date
  and a chapter-like label. That parses without knowing a site's markup, so there is no selector
  registry to maintain. マンガPark (9), マンガよもんが (5), ダ・ヴィンチニュース (3), ファイアCROSS (3), GANMA!(更新終了) (2), コミックノヴァ (2), COMIC熱帯 (1), マイナビニュース (1)

  The cost of generality is paid explicitly: every release carries `date_basis: heuristic` and
  `date_confidence: low`, a block without a chapter-like label is skipped, and volume announcements
  are dropped. It is not the kind of statement GigaViewer or FUZ make and is not recorded as one.

### Blocked, with the reason

HERO&#039;S Web (10), 新都社 (3), LINE マンガ インディーズ (1), comicグラスト (1), GetNavi (1), アサコミ (1), ドリコミ+ (1)

403 and 412 are bot protection; one host no longer resolves. Two others in this group turned out to
be plain timeouts and were recovered by retrying with a `Mozilla/5.0 (compatible; yurarium/0.1;
+…)` agent — the long-standing convention, which still names us and still links here. That is not
the thing refused for pixivコミック: that would mean claiming to be a browser to pass an access
control. This claims to be us, in the format the web expects.

### Open — the solution is rendering

pixivコミック (41), ガンガンONLINE (13), マガポケ (11), マンガワン (10), きら星ポータル (8), ヤングアニマルWeb (7), 裏サンデー (5), フラコミlike! (5), 少年ジャンプルーキー (4), ヤンジャン+ (3), コミックグロウル (3), ツイ4 (3), コロコロオンライン (2), コミックエッセイ劇場 (2), コミックPASH! neo (1), やわらかスピリッツ (1), NewsCrunch (1), pixivコミックマガジン (1), ゼロサムオンライン (1), マンガボックス (1), アルファポリス (1), Web漫画速報 (1), コロナEX (1), てれびくんヒーローコミックス (1), MAGKAN (1)

These are client-rendered: the chapter list is not in the HTML at any URL. The solution is the same
one identified for pixivコミック — render the page and read the DOM — and it is a solution, not a
dead end. What it costs is a browser in the pipeline, which is one decision taken once and then
covering all 25 hosts and 128 works at a stroke, pixiv's 41 among them.

That changes the arithmetic considerably from when it was weighed for pixiv alone. Recommended as
the next substantial piece of work.

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
