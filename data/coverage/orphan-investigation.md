# Two works in an inconsistent state

Working notes from 2026-08-04, appended as evidence landed. Read the state lines first.

- **プリンセ「ス」** — state: complete. Held again, from コミックノヴァ, and settled as `completed`.
- **惑星クローゼット** — state: complete for the verdict, open on the date. Settled as `completed`
  on BOOK☆WALKER's 完結 tag plus the NDL volume record. The month the serialisation ended is not
  established; see the open question at the end.

---

## プリンセ「ス」

Reproduced the failure before touching anything:

```
$ python3 adapters/names/test_curate.py
  FAIL    test_curate.py: 1 of 39
            and every title in it names a work we hold: got ['プリンセ「ス」'], want []
```

### What the page actually says

`https://www.123hon.com/nova/web-comic/princess/`, fetched 2026-08-04. 123hon.com serves no
robots.txt (404), so nothing is disallowed.

- One instalment is listed: `特別掲載　2022年04月01日更新`, free to read, linking to
  `https://www.123hon.com/vw/manga_award/princess/sv_pt0006242aefa1d5b9/index.html`.
- Beside the synopsis: 第一回 一二三書房マンガ大賞銀賞作品を特別掲載中. The synopsis is a girl in
  love with a tall, short-haired, boyish 王子さま who is herself in love with someone.
- The reader URL sits under `/vw/manga_award/`, not under the ordinary serialisation path.
- No author is credited, on the work page, in the WordPress REST record (`wp/v2/web-comic/682`,
  `acf` empty, `content` empty), or in the viewer's own metadata.

### The 2020-12-25 第8話 was never a chapter

`data/coverage/extract.yaml` recorded a chapter `連載シリーズ > プリンセ「ス」 … 2020年12月25日更新！
第8話 -->`. It is a hard-coded HTML comment in the site template. The identical comment, byte for
byte, sits on `https://www.123hon.com/nova/web-comic/mob/`, whose own live listing starts at 第1話
in 2021. The counter-case settles it: the string is template furniture, not a record of this work
having reached eight instalments.

### What the prize buys, which is the decisive fact

`https://www.123hon.com/nova/news_release/hifumi_manga_award1/`, the publisher's own announcement
of 第１回 一二三書房マンガ大賞 (entries 2021-08-16 to 2021-11-15, results announced around
2022-02-15), sets the prizes out:

| | |
|---|---|
| 大賞 | 賞金50万円 + WEB**連載**確約 + 紙出版確約 + 担当編集 |
| 金賞 | 賞金10万円 + WEB**掲載**確約 + 担当編集 |
| 銀賞 | 賞金5万円 + WEB**掲載**確約 |

銀賞 is promised a posting. Only 大賞 is promised a serialisation. So one instalment is the whole
of what this work was ever going to get on this platform, and its absence from a chapter list is
not a gap in our capture.

The submission rules accept 読切 or a serial's first chapter alike, so whether the manuscript itself
is a one-shot or a pilot is not decided by these two pages. What is decided is that no serialisation
began here.

### Nothing else carries it

- BOOK☆WALKER search for the exact title returns unrelated series. No tankobon, no licensed
  distributor edition.
- NDL OpenSearch by title matches nothing under this name (a title search folds to 9,151 hits on
  プリンセ, none of them this).
- The only URL any of our own files holds for it is the 123hon page.

### Disposition: held

It is a work under DEFINITIONS §6 — first published in Japan, on a commercial publisher's own web
platform, and one-shots are named in scope. The build already carries 399 rows at `state: oneshot`,
so a single-instalment work is not an anomaly here. What removed it was a confidence floor on
heuristic extraction, not a finding about the work.

**What was added.** `adapters/webpages/sites.yaml` gains コミックノヴァ as a site with its own
engine spec. The platform names each instalment in a `span.story-num` and prints the date beside it,
so the label is read from the element the publisher designated rather than reconstructed from a run
of scraped text. That is why `min_episodes: 1` is right here and the generic pass's floor of two is
right there: one dated block matched by pattern is usually the volume, and one label read from a
named element is the publisher stating it.

The date is required by the title selector rather than checked afterwards, because 猫魔法 withdraws
instalments in place: 第2話 through 第12話 keep their labels and replace the date with
公開は終了しました. A row with no date is not a dated release.

`adapters/webpages/releases.py` now strips HTML comments before parsing. Same fault, same pages, and
the other parser had already been fixed for it today: the stale copy of the list that コミックノヴァ
keeps in a comment parses perfectly well and is wrong, which is where the 猫魔法 record's third
chapter `第第1話(1/2)話` came from. Two parsers, one page, one rule. Pinned in
`adapters/webpages/test_releases.py`, with the counter-case that a live block containing a comment
must still be read.

`data/source/webpages/generic-www-123hon-com.yaml` is gone and
`data/source/webpages/comicnova.yaml` replaces it. Both of the host's works are carried over:
プリンセ「ス」 at 1 chapter and 猫魔法が世界に革命を起こすそうですよ? at 2. The generic pass skips any
host named in `sites.yaml`, so leaving the old file would have left an unowned record behind.

**State.** `completed`, on the prize terms above, recorded in `data/completion-reviewed.yaml` with
`source_kind: publisher-jp` and the announcement URL. It previously read `unsettled` on the ground
that the work page says no 完結 anywhere, which is true and was looking in the wrong place.

---

## 惑星クローゼット

つばな, serialised in 月刊コミックバーズ, collected by 幻冫舎コミックス, read on pixivコミック
`https://comic.pixiv.net/works/5365`. The state was `completed` on nothing but silence; pixiv lists
37 chapters against the 3 we hold, so the build correctly stopped claiming and read `unknown`.

### Evidence

**BOOK☆WALKER**, `https://bookwalker.jp/series/121180/list/`. Every one of the four volumes carries
the 完結 tag (tag 55), and the series' own tag summary counts コミックバーズ (4) and 完結 (4). A
licensed distributor stating that the series it stocks is finished.

Worth recording for whoever extends `adapters/bookwalker.py`: that adapter looks for 【完結】 in the
page title, and this page does not have it there. The marker is on the volumes. So the adapter's
silence about this series was not evidence of anything, exactly as its docstring says.

**NDL**, OpenSearch by title with the creator agreeing: 幻冬舎コミックス issued four volumes,
2017-07, 2018-07, 2019-04, 2020-04, and nothing after.

**Read together.** A stopped tankobon run is a fact about the print edition. Here it does not stand
alone: the shop selling that edition says the series is finished, and the two agree. The pixiv
listing of 37 chapters is the serialisation's full length rather than evidence of continuing
output, since our capture holds 3 of them and stops in 2018.

**State.** `completed`, recorded in `data/completion-reviewed.yaml` with `source_kind: licensor` and
the BOOK☆WALKER series URL.

### A build change this needed

The verdict did not apply at first. `build.py` set `state: unknown` for a work whose capture is
behind the platform's stated length, and returned before the hand-review lookup, which sat in the
branch below. So a short capture could suppress the better evidence. The review is now consulted
before that branch: `unknown` there is a statement about us, and a cited page saying the series
finished is a statement about the work.

### Open question

No `ended_on`. The last volume is 2020-04 and the final chapter must predate it, but no page reached
in this pass states the date the serialisation ended, and our own capture holds three chapters
stopping at 2018-12-18. Narrowing it means the 月刊コミックバーズ issue the last chapter ran in,
which is the next thing to look at. A month invented from the volume date would be a guess wearing
a citation.
