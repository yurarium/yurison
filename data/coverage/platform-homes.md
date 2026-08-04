# Platform homes: four misattributed or unlocated works

Research note, 2026-08-04. Everything below rests on a publisher, platform or shop page,
and each is linked. Community databases were used only to find candidates.

Summary of the finding that runs through all four items: several of our web captures are of
**secondary postings** — promotional excerpt runs, guest postings, licensed re-posts and
re-serialisations — rather than of the place a work is actually serialised. In three of the four
cases the secondary posting carries dates that describe the re-post, not the work.

---

## 1. 百合にはさまる男は死ねばいい!? (蓬餅, 幻冬舎コミックス)

### comicブースト series URL

**https://comic-boost.com/content/01280001**

Found by fetching https://comic-boost.com/sitemap.xml (present, 174 URLs, 161 of them
`/content/<8-digit id>` series pages) and reading the server-rendered `og:title` of each. The
site's own search is client-side, but the series pages themselves are server-rendered, so the
sitemap plus one request per series is a workable route for this host generally.

**Chapters listed: 7** — 第1話 through 第7話, every one dated **2023/05/19**, all 無料.

### But comicブースト is not the serialisation home either

The comicブースト page states its own status plainly:

> コミックス発売記念！ LINEマンガ発、大人気青春群像劇、第7話まで一挙特別出張掲載！

That is a **出張掲載** — a one-day guest posting of the first seven chapters to mark a tankobon
release. Under the 話 list the page carries a お知らせ block reading 「続きの連載はこちらから読めます！」
above a banner linking to `https://lin.ee/WFN3ut2/pnjo/fdp/1152`.

### The real home is LINE マンガ

That banner link 301s to an Adjust deeplink whose `adjust_redirect` parameter is
`https://manga.line.me/product/periodic?id=Z0001152`. So the publisher's own banner names the
LINE マンガ series id **Z0001152**.

**LINE マンガ series URL: https://manga.line.me/product/periodic?id=Z0001152**

I could not read that page: LINE マンガ returns **HTTP 412** with the body
「LINE マンガは日本でのみご利用いただけます」 (region-locked to Japan). I did not attempt to work
around it. So the chapter count and dates on LINE マンガ are **not established** here.

The publisher agrees on the origin. 幻冬舎コミックス's page for volume 7 describes the work as
「「次にくるマンガ大賞2023」webマンガ部門入賞！　LINEマンガ発の大人気青春群像劇」.

Sources:
- https://comic-boost.com/content/01280001 (comicブースト series page)
- https://comic-boost.com/sitemap.xml
- https://www.gentosha-comics.net/book/b655232.html (vol. 7, 2024-12-24, バーズコミックス, ISBN 9784344855182)
- https://www.gentosha-comics.net/book/b625089.html (vol. 1)
- https://manga.line.me/product/periodic?id=Z0001152 (refused, HTTP 412, region lock)

Note on volume count: our note says 7 volumes, but a volume 8 exists and is listed at retail as
published by **LINE Digital Frontier**, not 幻冬舎コミックス — see
https://www.cmoa.jp/title/268019/vol/8/ and https://bookwalker.jp/deb1ff260f-47e3-437c-8d07-91e218a18790/.
I did not find a 幻冬舎コミックス page for volume 8, so the publisher of volume 8 should be
treated as unconfirmed from a publisher source.

---

## 2. ダ・ヴィンチニュース (ddnavi.com) and コミックノヴァ (www.123hon.com)

**These two are not the same kind of site.** ddnavi is a promotion site; 123hon is a real
serialisation platform.

### ddnavi.com — ダ・ヴィンチWeb (KADOKAWA)

Our reading is correct. Each of these is a fixed-length excerpt run from an **already published
tankobon**, numbered 第1回, 第2回 … and explicitly labelled with its length. On
https://ddnavi.com/yurini-sinebaii/ the page states verbatim:

> 蓬餅著のコミック『百合にはさまる男は死ねばいい！？』から厳選して全4回連載でお届けします。

「厳選して」 — selected extracts. https://ddnavi.com/gyarumeido_akuyakureijo/ is headed **【全10回】**
and links out to BOOK☆WALKER for 試し読み, crediting the work to 百合姫コミックス/一迅社.

So ddnavi should not be treated as a serialisation home for anything. Our four ddnavi works and
their real homes:

| Work | Real home | Already in our data? |
|---|---|---|
| ギャルメイドと悪役令嬢 ～おじょーさまのハッピーエンドしか勝たん!～ (鍵穴) | 一迅プラス → **ichicomi.com**, series id `2550912965919360877` | **Yes** — `data/source/gigaviewer/ichicomi-series-feeds.yaml`, 15 chapters, 第15話【完結】 |
| 三角形の壊し方 (カボちゃ) | **U-NEXT Comic / ゼロスト** (paid 分冊版, no free web run); licensed re-post on カドコミ | **Yes** — `data/source/kadokomi/chapters.yaml`, https://comic-walker.com/detail/KC_005891_S |
| 君のためのカーテンコール (さとうしほ/恵茂田喜々) | 一迅プラス → **ichicomi.com**, series id `2550912965923184306`, label comic HOWL | **Yes** — `data/source/gigaviewer/ichicomi-series-feeds.yaml`, 16 chapters |
| 百合にはさまる男は死ねばいい!? (蓬餅) | **LINE マンガ** Z0001152; comicブースト 出張掲載 at /content/01280001 | **No** — ddnavi only. See item 1. |

So three of the four ddnavi captures are duplicates of a home we already hold, and the fourth is
the one genuine gap.

Sources:
- https://ddnavi.com/yurini-sinebaii/ (全4回連載 statement)
- https://ddnavi.com/gyarumeido_akuyakureijo/ (【全10回】)
- https://ichicomi.com/atom/series/2550912965919360877 — feed title 「一迅プラス（ギャルメイドと悪役令嬢 ～おじょーさまのハッピーエンドしか勝たん！～）」
- https://ichicomi.com/atom/series/2550912965923184306 — feed title 「一迅プラス（君のためのカーテンコール）」
- https://ichicomi.com/episode/2550912965923203959 (第1話, comic HOWL label)
- https://comic-walker.com/detail/KC_005891_S — カドコミ, 3 episodes, describes the work as 「U-NEXT発の人気コミック」
- https://publishing.unext.co.jp/comic/title/HGKNWmgxzgVULQigQGuTQ (U-NEXT Publishing official page)
- https://publishing.unext.co.jp/comic/title_list/zerosuto (ゼロスト is a **label**, not a reading site — chapters sell as 分冊版)

Note: `ichijin-plus.com` URLs now 301 to `ichicomi.com` (e.g.
https://ichijin-plus.com/comics/140594018976160 → https://ichicomi.com/episode/2550912965919401444).
ichicomi is a GigaViewer instance and its series listing links to `/episode/<id>`, not to a
`/series/<slug>` path; the numeric series id in the atom URL is the stable handle.

Second note, possibly worth a separate look: the ichicomi atom feeds date **every** chapter of both
works to 2025-08-08 / 2025-08-09, which is the ichijin-plus → ichicomi migration, not the original
publication. Same class of problem as item 4 below.

### www.123hon.com — コミックノヴァ (一二三書房)

**Not the same kind of thing.** コミックノヴァ is 一二三書房's own web manga site: it carries
「毎週金曜日 夕方ごろ更新!」, numbers instalments 第1話, 第2話 … and rotates old chapters off with
「公開は終了しました」. It is a genuine serialisation platform whose back catalogue is withdrawn,
which is why our capture of it looks thin.

Works we hold from it:

- **猫魔法が世界に革命を起こすそうですよ?** — https://www.123hon.com/nova/web-comic/nekomaho/
  Original comicalization serialised here (原作 海野アロイ / 漫画 かやこ), collected as
  ノヴァコミックス. Only 第1話 (in two parts) is currently readable; 第2話–第12話 show
  「公開は終了しました」. **This is its real home** — no other serialisation venue found.
  Volumes: https://bookwalker.jp/series/459252/list/
- **プリンセ「ス」** — https://www.123hon.com/nova/web-comic/princess/
  Posted as 特別掲載 dated 2022-04-01, credited as 第一回 一二三書房マンガ大賞銀賞作品.
  A prize-winner posted by the publisher; **also its real home**, no elsewhere found.

Both of our chapter rows for these are heuristic scrapes and mis-parse the page badly
(e.g. the title `更新！ 第8話 -->` and `第第1話(1/2)話`), but the platform attribution is right.
Recommendation: keep 123hon as a platform; drop ddnavi as a platform.

---

## 3. ベイビー車中ハッカーズ (たびれこ)

### ynjn series URL

**https://ynjn.jp/title/16787** — full chapter list at **https://ynjn.jp/allEpisodeList/16787**

The header there reads **全47話**. The newest is

**第19話 (3)星空の記憶** — https://ynjn.jp/viewer/16787/305694

### Its date: not established, and ynjn does not publish one

ynjn.jp is a Nuxt app; I read its hydration payload directly. Each episode object carries
`id`, `name`, `cost`, `imageUrl`, `readingCondition`, `linkTo` and the various access booleans,
and **no date field of any kind**. A regex for `更新` and for any `20\d\d` date over the whole
`window.__NUXT__` state returns nothing. There is no date in the rendered DOM either. So ynjn is a
dateless source; a capture of it can attest chapter existence and order but not timing.

### What our tonarinoyj capture actually is

Our record is not truncated — it is complete and correct for what it covers.
https://tonarinoyj.jp/atom/series/2550912964606689260 still contains exactly **2** entries
(第1話 2024-09-18, 第2話 2024-10-16). The となりのヤングジャンプ series page describes the work as
**〈ウルトラジャンプ連載作品〉**, so those two chapters are a promotional free posting of a magazine
serialisation, not a web serialisation that stalled.

### The actual serialisation

**ウルトラジャンプ** (monthly, 集英社). The magazine's own series page,
https://ultra.shueisha.co.jp/manga/manga-7355/, links to https://ynjn.jp/title/16787 as the place
to read it. Volumes, ヤングジャンプコミックス:

- vol. 1 — https://www.shueisha.co.jp/books/items/contents.html?isbn=978-4-08-893559-1
- vol. 2 — https://www.shueisha.co.jp/books/items/contents.html?isbn=978-4-08-893756-4
- vol. 3 — https://www.shueisha.co.jp/books/items/contents.html?isbn=978-4-08-894141-7 — **2026-03-18**, stated 「ウルトラジャンプ掲載」
- vol. 4 — listed as **2026-08-19** on https://ultra.shueisha.co.jp/manga/manga-7355/

There is also a ニコニコ漫画 posting (ウルトラジャンプ ニコニコ版) at
https://manga.nicovideo.jp/comic/71924, which is dated but carries only 2 free episodes
(第2話, 2025-02-25) and so is no use as a spine.

So: alive, yes, but the live web home is ヤンジャン＋, and **no platform we can reach dates the
newest chapter**. The most recent dated evidence of the run is the vol. 4 release date of
2026-08-19.

---

## 4. 夜と海 (郷本)

**Resolved: the COMIC FUZ chapter list is re-dated. There is no contradiction and no second
edition.** The work finished in 2021; FUZ re-ran it from scratch in 2024.

The FUZ page https://comic-fuz.com/manga/517 interleaves volume markers into the chapter list, and
the two date series sit side by side:

| Volume marker (on the same page) | Release date |
|---|---|
| 夜と海 １巻 | **2018/08/09発売** |
| 夜と海 ２巻 | **2019/07/16発売** |
| 夜と海 ３巻 | **2021/04/15発売** |

and immediately below each marker, the chapters that volume contains, dated:

- 第1話 — **2024/05/30**
- 第2話(1) 2024/06/06 … 第5話(2) 2024/07/25 *(these sit under the 1巻 marker)*
- 第6話(1) 2024/08/01 … 第11話(2) **2024/10/17** *(under the 2巻 marker)*
- 第12話(1) through 第19話(2) — **no date at all**, all marked 先読み and paywalled
  (our capture records these as `access_modes: ["purchase"]` with
  `pointConsumption type=2 amount=60`, and indeed carries no `updated` for them, which is correct)

That is the signature of a re-serialisation: one part per week every Thursday (the page's own
tag is 木曜日) starting 2024-05-30, walking a completed three-volume work back out from
第1話. Our 37-chapter capture with `latest_updated: 2024-10-17` is an accurate record of the
**FUZ re-run**, and the 2021 volume 3 date is an accurate record of the **original edition**.
Both are true. Only the interpretation "this work was still producing new chapters in October
2024" is wrong.

Original publication: 芳文社, ラバココミックス label (the FUZ page shows the tag ラバココミックス),
3 volumes, completed. COMIC FUZ is 芳文社's own platform, so the re-run is a first-party reissue.
The specific original web venue (reported as the ラバコ web magazine) I could **not** confirm from a
publisher page and do not assert.

Sources:
- https://comic-fuz.com/manga/517 (chapter dates, volume dates, 先読み markers, ラバココミックス tag; rendered in a browser — this page is client-rendered and returns only chrome to a plain fetch)
- https://bookwalker.jp/series/169632/ (【完結】夜と海（ラバココミックス）)
- https://www.kinokuniya.co.jp/f/dsg-01-9784832236271 (芳文社コミックス 夜と海 〈１〉)

### Suggested general rule from this item

A chapter list whose ids are one contiguous block (ours run 55046–55142 with a uniform stride of 3)
and whose dates begin long after the work's last tankobon is a re-run, not a live serialisation.
That test would also have caught the ichicomi bulk-dating noted in item 2.

---

## Things not established

- The LINE マンガ chapter count and dates for 百合にはさまる男は死ねばいい!? — page is region-locked (HTTP 412).
- Any date for the newest ベイビー車中ハッカーズ chapter — ynjn publishes none, in the DOM or in its state.
- The publisher of 百合にはさまる男は死ねばいい!? volume 8 (retail says LINE Digital Frontier; no publisher page found).
- The original web venue of 夜と海 beyond the ラバココミックス label.
