# Retailer classification: initial reconnaissance

Retrieved 2026-08-04. Two shops probed for a yuri classification usable as an inclusion basis,
after the decision to admit retailer classification alongside the imprint route.

Both shops are read at their public listing pages with `yurarium/0.1`. cmoa's robots.txt disallows
only account, basket and reader paths, none of which are touched here. BOOK☆WALKER's listings are
already read by `adapters/bookwalker.py` for completion markers.

## コミックシーモア classifies yuri as a sub-genre

`/search/genre/37/` is 百合・GL and holds **1,869 titles**. It is reachable from any work page,
where it sits beside the demographic genre, and it does not appear in the facet block on a search
result, which is why a first pass over the search page missed it.

Its own genre facet reads 青年(656), 女性(585), 少女(546), 少年(82) and no アダルトマンガ at all,
so the shop's yuri genre is all-ages by construction. 百合コレ contributes 593 items here against
782 in the label as a whole, and the 189-item difference is close to the 181 the label files as
adult, which is the same statement from the other side.

The keyword route is worthless by comparison: 5,061 items, of which 1,161 are 青空文庫 texts by
宮本百合子. The keyword matches personal names.

Alongside the genre, the shop holds a label index, and it knows more yuri labels than MADB gave us:

| Label | Items | Publisher |
|---|---|---|
| 百合コレ | 782 | ナンバーナイン |
| 百合姫コミックス | 434 | 一迅社 |
| BLIC-GL | 119 | クロスフォリオ出版 |
| 百合缶 | 44 | ブックウォーカー |
| GL★オトメチカ | 10 | CLLENN |
| 少女宣言(百合シリーズ) | 7 | 秋水社ORIGINAL |

A label is the publisher's own imprint, so these are publisher-side and raise no question under
DEFINITIONS §4. They widen the existing imprint route from one imprint to six.

### The adult genre flag under-reports

百合コレ is a doujinshi label: all 782 items come from ナンバーナイン, a doujin distributor. Only
181 are filed アダルトマンガ, and the remainder are not thereby clean. One item on the first page is
titled with 【棒消し修正版】, an adult doujinshi re-edited to erase genitalia so it clears the
all-ages filter, and it is filed 青年マンガ. So `genre != アダルト` does not separate pornography
from the rest, and any rule resting on that flag would admit censored porn with a citation attached.

百合缶 files 42 of its 44 items as TLマンガ, and GL★オトメチカ 5 of 10, so the smaller labels are
adult-adjacent by their own classification.

## BOOK☆WALKER has a real one

Tag 14 is 百合, presented under 書籍ジャンル on each series page. This is the shop's own genre
classification, which is the thing the imprint route cannot supply.

| Facet | Items |
|---|---|
| 百合 (all) | 2,391 |
| manga only (`qcat=2`) | 2,153 |
| 同人誌・個人出版 (`qtag=1083`) | 378 |
| 完結 (`qtag=42`) | 486 |

Listings are server-rendered, 60 to a page, and `?page=N` returns disjoint sets, so about 36 pages
covers the manga shelf. Entries carry the imprint in parentheses, and the first page alone spans
FUZコミックス, バンブーコミックス, 百合姫コミックス, まんがタイムKRコミックス and
角川コミックス・エース, which is the publisher spread the discovery half of the print work needs.

R18 stock lives on the shop's separate adult store, so this shelf is already all-ages.

**The doujin facet is not the doujin fraction, and an earlier version of this note said it was.**
Corrected 2026-08-04 by the capture. `qtag=1083` holds 276 rows spread over 86 small imprints, and
百合コレ, which is 516 rows of this shelf and is published by the doujin distributor ナンバーナイン,
carries none of them. So subtracting the facet is not the mechanical exclusion claimed here
originally. It is a partial signal, and whatever rule replaces it has to be decided rather than
read off the shop. `ダイレクト出版` (`qtag=1038`) is the same set of rows, not a second one.

## Adult tagging against what we already accept

Both cmoa shelves were pulled and matched against the 992 works in `data/build/series.json`, on a
title key that folds width, strips bracketed edition markers and drops volume numbers. The matcher
was checked against works known to sit on each shelf before its answers were believed.

| | |
|---|---|
| Works we hold that carry cmoa's adult genre | **0** of 992 |
| Works we hold on the 百合・GL genre shelf | 175 of 992 |
| Titles on both the yuri and the adult shelf | 9 |

Zero is the headline. Nothing in the corpus is filed adult by the shop, and that includes the two
titles that prompted the question: `彩純ちゃんはレズ風俗に興味があります！` and
`昨日シたのに覚えてないの？ 百合えっち短編集` both sit on the all-ages yuri genre. So the shop's
line and ours already agree, and cmoa's adult genre marks 成人向け material rather than sexual
content in general. 175 rather than a larger number reflects print availability: most of the corpus
is web-serialised and has no volume for a shop to stock.

The 9 dual-listed titles are the interesting ones, because they are not 9 works. They are edition
twins, one 【棒消し修正版】 or 【R-18版】 of the other, so the same work is filed adult in its
uncensored edition and yuri in its censored one. The boundary the shop draws is between editions,
not between works.

That leak is small where it announces itself: of the 1,868 titles on the yuri shelf, 4 carry a
censorship marker and 1 an R18 marker. It is only measurable at all for works that say so in the
title, so treat these as a floor.

## The exclusion boundary is not where it was assumed to be

The standing rule is that works marketed or intended as pornography are excluded and never
uploaded. Two things this recon establishes:

Doujin is a good proxy for where the pornography is, and it is separable at BOOK☆WALKER. It is not
separable at cmoa, and the 【棒消し修正版】 case shows the shop's own adult flag is not a boundary.

The proxy is also incomplete in the other direction. The corpus already holds
`昨日シたのに覚えてないの？ 百合えっち短編集` and `彩純ちゃんはレズ風俗に興味があります！`, both
commercially published, neither doujin, and both arrived through the existing publisher route. So
the exclusion is not implemented anywhere today, and widening the corpus does not create the gap so
much as make it operational.

## Placement in the taxonomy, and why it is a sourcing hazard

cmoa's taxonomy page lists 27 top-level genres. BLマンガ and BL小説 are both on it. Yuri is not on
it at any level, and genre 37 is reachable only from a work page or from a link somebody already
holds.

Catalogue size does not explain the placement. BL is much the larger shelf at 41,280, but the test
is against the small genres that do get top billing:

| Genre | Titles | Top level |
|---|---|---|
| BLマンガ | 41,280 | yes |
| TLマンガ | 22,338 | yes |
| ハーレクインコミックス | 6,870 | yes |
| レディコミ | 6,571 | yes |
| ライトアダルト | 2,839 | yes |
| **百合・GL** | **1,869** | **no** |
| 映画化 | 1,733 | yes |
| ドラマ化 | 1,578 | yes |
| グリム童話 | 587 | yes |

百合・GL outranks three top-level genres, and グリム童話 is under a third its size with a slot of
its own. Whatever decides placement here, it is not the size of the shelf.

BOOK☆WALKER does not repeat it. Its tag space is flat, with 完結, 青年マンガ, 同人誌・個人出版 and
週刊少年ジャンプ all tags alongside each other, so there is no top level to be left out of. 百合 is
a first-class 書籍ジャンル tag carrying 5,442 books, 64th of the 876 tags by size. Where BL sits at
BOOK☆WALKER was not established: it is not among the 100 largest tags.

**The consequence for sourcing.** Where a taxonomy hides yuri, an absent yuri category is not
evidence of absent yuri stock, and reconnaissance that reads only the top level will file the
source as having nothing. That is this project's characteristic failure with a new face, and it
caught this recon: the first pass over cmoa concluded there was no yuri classification, from a
facet block that genuinely does not contain one, while 1,869 titles sat behind a link on every work
page. Treat "no yuri category" at any new source as unproven until a work page has been read.

## Reading

Two independent retailer classifications exist, cmoa genre 37 at 1,869 titles and BOOK☆WALKER tag
14 at 2,153 manga titles, and both are server-rendered and paged. Take both, since agreement
between two shops is a stronger basis for a work than either alone, and the disagreements are worth
looking at directly.

Each excludes pornography by its own construction, cmoa by filing adult in a genre its yuri genre
does not contain, BOOK☆WALKER by keeping R18 on a separate store. Neither excludes doujin, and
neither shop's own metadata identifies its doujin stock reliably: BOOK☆WALKER's facet misses the
largest doujin imprint on the shelf, and cmoa's publisher field identifies ナンバーナイン but leaves
seven further indie distributors unestablished. Doujin identification is a judgement this project
has to make about publishers, and it is the open piece of work here.

Neither shelf is complete, either. コンカフェ嬢は恋を着る is stocked by BOOK☆WALKER, marked 完結,
held in this database, and absent from tag 14, so the tag is applied by hand and its absence says
nothing.

Keep the basis in the record so a reader can tell whether a work is in because a publisher called
it yuri or because a shop shelved it there.
