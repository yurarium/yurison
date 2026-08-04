# Author readings, round 4

78 names checked. 45 readings found, 33 not found.

Of the 45 found, 15 differ from the machine guess in kana, not merely in spacing. The two worst
were 行翔葉, stored アキバ ジロ, which is あきばじろぉ, a different artist who happens to have drawn
a work also called シャッターチャンス, and 逆縞, stored ギャク シマ, which reads サカシマ. The rest
are surname or given-name readings the guesser picked wrongly (縁山 エンヤマ for ヘリヤマ, 最遠エト
サイエン for サイトオ, 朝和 アサカズ for アサワ, 杜若彩 カキツバタ アヤ for カキツバタ サイ,
結城結月 ユウキ ケツ ガツ for ユウキ ユヅキ, 須藤碧 スドウ ミドリ for スドウ アオイ, 桃枝司
モモエシ for モモエ ツカサ, 弐尉マルコ ニ ジョウ for ニイ, 岩矢滉汰朗 コウタ アキラ for
コウタロウ, 甲斐冬雪 カイ フユ for カイ フユキ) or word-boundary splits inside a name that is one
unit (皐月木獏 サツキ キ バク for サツキギ バク, 蒼いち アオ イチ for ソウイチ, 橘まなり
タチバナノ for タチバナ).

One entry needs a decision beyond furigana. 時一二 is not Japanese. The National Diet Library
authority record gives the name only as Shi, Yi Er and its catalogue record for キャンディ marks
the original language as Chinese, so NDL deliberately recorded no kana. The stored トキ イチニ
should be dropped rather than replaced.

The 33 not found are mostly artists whose only credits are web one-shots or contest entries on
少年ジャンプ＋, ジャンプルーキー!, サンデーうぇぶり, コミックDAYS, 一迅プラス, DAYS NEO and
カドコミ. Those works carry no ISBN, so NDL holds nothing under the name and the platform pages
print the pen name without a reading. Two are blocked the other way: 西村隆 and 黒木翔 both return
many NDL records under the exact characters, all of them academics or a credit with the reading
field left blank.

Method: `https://ndlsearch.ndl.go.jp/api/opensearch?creator=<name>`, falling back to `?title=<work>`
and `?any=<name>` when the creator index was empty, reading `dcndl:creatorTranscription` beside
`dc:creator`. The change that mattered this round was pairing the two element lists positionally
rather than reading the record as a whole. Magazine issue records on NDL list every contributor to
that issue with a transcription each, in order, so an artist with no book of their own still yields
a catalogued reading through the issue they appeared in. That alone resolved 涼風そら, 結城結月,
岩矢滉汰朗, 須藤碧, 朝和, 甲斐冬雪 and 藤田直樹. Every record was checked against the other titles
on it to rule out a namesake. Requests went out as `yurarium/0.1` at roughly 1.6s apart.

x.com returned HTTP 402 to this client on every attempt, so the two X handles cited below are read
from search result titles rather than fetched. Both only corroborate a reading that another source
already carried.

| name | machine guess | proposed reading | source kind | URL | note |
|---|---|---|---|---|---|
| 古目印箱 | フル メジルシ バコ | NOT FOUND | | | NDL creator, title `ねむれる友達` and free text all empty. No book, no publisher page located. |
| 狼 | オオカミ | NOT FOUND | | | NDL creator returns 30+ records, every one a different name containing 狼 (狼森圓, 狼太郎, 竜炎狼牙). Title `梓月は天に咲う` empty. |
| あの冨田 | アノ トミタ | NOT FOUND | | | NDL creator, title `綺麗な花の遺し方` and free text all empty. |
| まゃ～吾郎 | マ ャ ～ ゴロウ | NOT FOUND | | | NDL creator, title `ぷれいめ～と` and free text all empty. |
| 一世蕨 | カシ ミチヨ | NOT FOUND | | | NDL creator empty; title `あなたのとなり` returns only unrelated works. Guess is a different person's name and should be dropped. |
| 上田さかひら | ウエダサ カ ヒラ | NOT FOUND | | | NDL creator empty; title `熱演` returns only newspaper articles. |
| 京村秋 | キョウソン アキ | NOT FOUND | | | NDL creator empty; title `日陰のふたり` returns a film soundtrack only. |
| 伊藤玄採 | イトウ ゲン サイ | NOT FOUND | | | NDL creator, title `てぇてぇ二人` and free text all empty. |
| 免条ユウ | メン ジョウ ユウ | NOT FOUND | | | NDL creator, title `濡鴉の魔女` and free text all empty. Web search found no publisher page for the work. |
| 千図丸 | チズマル | NOT FOUND | | | NDL creator empty; title `ひみつのまんが` returns only the Kyoto manga museum guide. |
| 双葉ヤヒコ | フタバ ヤヒコ | NOT FOUND | | | NDL creator empty; title `滅亡カウントダウン` returns unrelated works. |
| 和郷梓 | カズサト シ | NOT FOUND | | | NDL creator, title `白装の悪魔` and free text all empty. ジャンプルーキー! contest entry, no catalogued work. |
| 坂城 | サカキ | NOT FOUND | | | NDL creator returns 坂城町教育委員会 and 大阪城天守閣, never a manga artist. Title `御羊ちゃんは触りたい` empty. |
| 壱弎ハルヒト | イチ サン ハルヒト | NOT FOUND | | | NDL creator, title `其れの手も借りるほど` and free text all empty. |
| 外園暁 | ホカゾノ アキラ | NOT FOUND | | | NDL creator, title `スーパーナックルお嬢様` and free text all empty. JUMP新世界漫画賞 entry only. |
| 安藤 優 | アンドウ ユウ | アンドウ ユウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029566904 | NDL record for the example work itself, 集英社. Creator index is crowded with 安藤優子 and 安藤優一郎; the title query isolates the right person. |
| 宮部サチ | ミヤベ サチ | ミヤベ サチ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I8211DV00CALEG013000X | 57 aligned records, ぶんか社 comic meltyKILL run plus 32歳主婦、推しと100万円でデートする. |
| 小形朱嶺 | オガタ アカネ | オガタ アカネ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033838420 | 若葉さんちの青い恋, 小学館. Same Sunday orbit as the example work. |
| 尾野凛 | オノ リン | オノ リン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032675315 | 芳文社, plus クラスで2番目に可愛い女の子と友だちになった. |
| 岡村アユム | オカムラ アユム | オカムラ アユム | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I028542437 | 天使も定時で帰りたい!!, 実業之日本社, 12 aligned records. |
| 岩矢滉汰朗 | イワヤ コウタ アキラ | イワヤ コウタロウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I09Y244850000d0000000 | 月刊!スピリッツ 2024年5月号 contributor list. Matches the example work's スピリッツ賞 credit. Guess split 汰朗 into two words. |
| 嶋鳥ひとり | シマ トリ ヒトリ | NOT FOUND | | | NDL creator and free text empty. DAYS NEO author page (daysneo.com/author/sima1128/) prints the name with no furigana. |
| 弐尉マルコ | ニ ジョウ マルコ | ニイ マルコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I024943213 | KADOKAWA, 60 aligned records across the ガールズ&パンツァー spin-off. 弐尉 is ニイ, not ニジョウ. |
| 徳永パン | トクナガ パン | トクナガ パン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031281415 | KADOKAWA; the same creator index also holds モブヘブン【分冊版】, the example work. |
| 文川あや | フミカワ アヤ | フミカワ アヤ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033251625 | その蒼を、青とよばない, ヒーローズ. |
| 星文ろの | ホシフミ ロ ノ | ホシフミ ロノ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033897302 | 実業之日本社; also 僕らは恋に落ちる瀬戸際で. Same kana, one word not two. |
| 時一二 | トキ イチニ | NOT FOUND | | https://id.ndl.go.jp/auth/ndlna/033156996 | Not a Japanese name. NDL authority gives only Shi, Yi Er, and the キャンディ record sets `dcndl:originalLanguage` to `chi`. Furigana does not apply; drop the stored guess. |
| 最遠エト | サイエン エト | サイトオ エト | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031773643 | 双葉社, 10 aligned records on one series. Only 最遠エト in NDL and a manga artist, so the identity holds, though the example work is a 少年ジャンプ＋ one-shot rather than this series. |
| 朝和 | アサカズ | アサワ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06A0000000000601047A | アフタヌーン 2023年2月号 and 2023年9月号 contributor lists. The example work is a コミックDAYS one-shot, the same 講談社 group and the same years, and no other 朝和 appears as a manga creator. Identity is strong but rests on that context, not on a shared title. |
| 木野免 | キノメン | NOT FOUND | | | NDL creator, title `白けた夜` and free text all empty. ヤングスペリオール新人賞 entry only. |
| 杜若彩 | カキツバタ アヤ | カキツバタ サイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034411725 | スターツ出版. Corroborated by the artist's own X handle @kakitsubatasai, whose account lists ノゾミとカナエ, the example work, among their credits. Two sources agree on サイ. |
| 東金桜 | トウガネ サクラ | トウガネ サクラ | author | https://x.com/togane_sakura | No NDL holding; the 百合姫 one-shot has no ISBN. The artist's own handle romanises the name, confirming the guess. x.com refused this client with HTTP 402, so the handle is read from search result titles rather than fetched. |
| 柴田康平 | シバタ コウヘイ | シバタ コウヘイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04736579A10086900000 | 青騎士 第1号. NDL separately holds 魔女とくゅらす, the example work, under 柴田, 康平 / シバタ, コウヘイ. Distinguished from several academic namesakes by those two manga records. |
| 桃枝司 | モモエシ | モモエ ツカサ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I09D151390000d0000000 | 小学館; the same index holds 抱かれたい女, the example work. 司 is ツカサ, a given name, not part of the surname. |
| 梨尾 | ナシオ | ナシオ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031381081 | ぶんか社, and the record is the example work itself. |
| 椿木とりか | ツバキ トリカ | ツバキ トリカ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06Z0139917410001000N | ARIA 2017 issues; NDL also holds ケモノとワルツ, the example work. |
| 横森もよこ | ヨコモリ モ ヨコ | ヨコモリ モヨコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784107729675 | 先輩と後輩、大暴れの日々, 新潮社, the collected form of the example work. Same kana, one word not two. |
| 橘まなり | タチバナノ マナリ | タチバナ マナリ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033028481 | 芳文社, 4 aligned records. Guess added a spurious の. |
| 櫻井 | サクライ | サクライ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031966718 | The record is 魔王と百合 itself, KADOKAWA. Creator index for 櫻井 is useless, hundreds of unrelated people; the title query pins it. |
| 水山めろ | ミズヤマ メロ | ミズヤマ メロ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034044854 | KADOKAWA, the example work 恋色の境界 itself. |
| 永田さんずい | ナガタ サンズイ | ナガタ サンズイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A26321700000 | KADOKAWA, ライバルアライバル, the example work. |
| 沖田冬 | オキダ フユ | NOT FOUND | | | NDL creator, title `かんかく` and free text all empty. ジャンプルーキー! entry only. |
| 波 | ナミ | NOT FOUND | | | NDL creator returns only names containing 波 (難波, 池波, 江波). Title `外側偏重` empty. |
| 涼風そら | スズカゼ ソラ | スズカゼ ソラ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06A0000000000961495H | 別冊少年マガジン 2025年12月号 contributor list, last entry, consistent with a new one-shot. Confirms the guess. |
| 潤海そら | ウミ ソラ | NOT FOUND | | | NDL creator, title `ココロメイク コスメティカ` and free text all empty. |
| 猫田れくら。 | ネコタレ クラ。 | NOT FOUND | | | NDL empty. カドコミ and ニコニコ漫画 both carry 愛する貴方はキメラ but print the pen name with no reading. Guess also mis-splits the name and keeps the trailing 。 in the kana. |
| 甲斐冬雪 | カイ フユ | カイ フユキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06A0000000000412191I | 講談社; NDL separately holds 恋とポテトと夏休み and 変身人間ちえ under カイ, フユキ. Guess dropped the final キ. |
| 皐月木獏 | サツキ キ バク | サツキギ バク | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A24824900000 | KADOKAWA, 外来魔法生物対策課. NDL writes the boundary as 皐月木, 獏, so the surname is three characters. |
| 矢坂しゅう | ヤサカ シュウ | ヤサカ シュウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I030707279 | 竹書房; the same index holds バカに告白【分冊版】, the example work. |
| 神戸いちご | コウベ イチゴ | NOT FOUND | | | NDL empty. The 一迅プラス page for あこがれを結んで prints the name with no reading. Their X handle @ichigokanato15 suggests カナト rather than コウベ for 神戸, which is enough to distrust the guess but not enough to assert a reading. |
| 空木帆子 | ウツギ ホコ | ウツギ ホコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032123879 | 異類の友: 空木帆子よみきり集, 小学館. |
| 箭坪幹 | ヤツボ ミキ | ヤツボ ミキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033691799 | 廻天のアルバス, 小学館. Also credited in サンデーmini, matching the Sunday context of the example work. |
| 結城結月 | ユウキ ケツ ガツ | ユウキ ユヅキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I09Y244920000d0000000 | 月刊!スピリッツ 2024年12月号 and 2025年12月号 contributor lists agree. Guess read 結月 as on-yomi. |
| 縁山 | エンヤマ | ヘリヤマ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I2530000D0019600010A1 | 秋田書店, 阿佐ヶ谷サキュバス同人物語, the example work, 55 aligned records. 縁 is ヘリ here. |
| 老田ヒビキ | オイタ ヒビキ | NOT FOUND | | | NDL creator, title `魔法少女リインカーネーション` and free text all empty. |
| 芝浦晴海 | シバウラ ハルミ | シバウラ ハルミ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A24089300000 | KADOKAWA, サバイブとマリーミー, 36 aligned records. Only 芝浦晴海 in NDL and a manga artist. |
| 花束葬式 | ハナタバ ソウシキ | ハナタバ ソウシキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034008845 | 芳文社; also マダム表裏の恋愛サロン. |
| 若林アスカ | ワカバヤシ アスカ | NOT FOUND | | | NDL creator, title `クラス全員で百合カプを守る話` and free text all empty. |
| 茂木清香 | モギ サヤカ | モギ サヤカ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I025639662 | 双葉社 青の母, plus ITAN issues and ガールミートガール, the example work. Note this is モギ, not モテギ. |
| 蒼いち | アオ イチ | ソウイチ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A22719000000 | KADOKAWA, 23 aligned records. Same characters, but one word ソウイチ rather than アオ + イチ. |
| 藤崎ろと | フジサキ ロ ト | フジサキ ロト | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784575441307 | 双葉社; also VTuberなんだが配信切り忘れたら伝説になってた. Same kana, one word not two. |
| 藤田直樹 | フジタ ナオキ | フジタ ナオキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06A0000000000020149J | The creator index is dominated by academic namesakes. Identity fixed by BEAT & MOTION, the artist's 集英社 tankobon, and by the アフタヌーン 2018年4月号 contributor list, both reading フジタ, ナオキ. |
| 行翔葉 | アキバ ジロ | ユキ ショウヨウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031785471 | ふぞろい僕らは嘘をつく, 小学館 サンデーうぇぶりSSC. The stored guess is あきばじろぉ, a different artist who drew an unrelated work also titled シャッターチャンス. This one is a wrong-person error, not a wrong-reading error. |
| 西村隆 | ニシムラ タカシ | NOT FOUND | | | NDL creator returns 30+ records under the exact characters, every one an academic (西村隆夫, 西村隆一, 西村隆雄). Title `ランドエスケープ` returns only music scores. No way to isolate the artist. |
| 誇大逸 | コダイ イツ | NOT FOUND | | | NDL creator, title `セパレートユニフォーム` and free text all empty. |
| 谷川ニコ | タニガワ ニコ | タニガワ ニコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I09D093950000d0000000 | 小学館, 48 aligned records including クズとメガネと文学少女〈偽〉. |
| 逆縞 | ギャク シマ | サカシマ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033539328 | KADOKAWA, and the record is 副会長の主なお仕事, the example work. Guess used on-yomi for 逆. |
| 金城まち | キンジョウ マチ | NOT FOUND | | | NDL creator and title empty. The name appears in the コミック百合姫 2026年8月号 free-text hit, but that record credits only コミック百合姫編集部, with no per-contributor list. |
| 鉄一 | テツカズ | NOT FOUND | | | NDL creator returns only names containing 鉄一 (朝香鉄一, 脇鉄一, 梶川鉄一郎). Title of the example work empty. |
| 阿東里枝 | アトウ リエ | アトウ リエ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031255967 | うそつきアンドロイド, 秋田書店, recorded as 阿東, 里枝, 1991- / アトウ, リエ, 1991-. Confirms the guess. |
| 雪見とおる | ユキミ ト オル | NOT FOUND | | | NDL creator, title `こもぐちゃんに食べられたい` and free text all empty. |
| 須藤碧 | スドウ ミドリ | スドウ アオイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06A0000000000963977O | good!アフタヌーン 2025年12号 contributor list, last entry. 碧 is アオイ here, a given name, not ミドリ. |
| 高瀬わか | タカセ ワカ | タカセ ワカ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033374630 | 姉のともだち, 集英社, 55 aligned records including イブニング issues. |
| 鬼龍駿河 | キリュウ スルガ | キリュウ スルガ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034614650 | KADOKAWA, and the record is 甘やかせ魔族ども, the example work. |
| 鳩豆 | ハトマメ | NOT FOUND | | | NDL creator empty; free text returns only a drama CD subtitle and unrelated books. Title `同星生殖` empty. |
| 黒木翔 | クロキ ショウ | NOT FOUND | | | NDL holds サンデーmini サンデーS増刊2023年9月号 crediting 黒木/翔, but that record carries no transcription at all. Every other 黒木翔 in NDL is an academic. The example work is a 少年サンデーS one-shot on サンデーうぇぶり with no reading printed. |
| 森みなも | モリ ミナ モ | NOT FOUND | | | NDL creator returns 水森みなも (ミナモリ, ミナモ) and the アフタヌーン 2024年9月号 list contains 高森みなも (タカモリミナモ), neither of which is 森みなも. Title `悪いことを考えている` empty. The guess is not corroborated and two near-namesakes make it risky. |
| 灰田高鴻 | ハイダ コウコウ | ハイダ コウコウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06A0000000000866871N | 講談社; NDL also holds 灰かぶりの天使, the example work, and スインギンドラゴンタイガーブギ. Confirms the guess. |
