# Author readings, round 3

79 names checked. 39 readings found, 40 not found.

Of the 39 found, 16 differ from the machine guess. Two of those were badly wrong: 舟本絵理歌 was
stored as マロ, which is a different artist's name entirely, and 灯 was stored as アカリ but the
publisher prints アカシ. The remaining differences are surname readings the guesser picked wrongly
(宮原都 ミヤハラ ト for ミヤハラ ミヤコ, 雪宮ありさ ユキグウ for ユキミヤ, 沖田さとり オキダ for
オキタ, 茂木ヨモギ モテギ for モギ, 桜内美優 サクラウチ for サクライ, 杉谷ユカリ スギタニ for
スギヤ, 観乃ふみ ミ ノ for カンノ) or word-boundary splits inside a name that is really one unit
(紫のあ, 尾羊英, 郷本, 島, 浮足, 葛城かなで).

The 40 not found are almost all artists whose only credits are web one-shots or serials on
サンデーうぇぶり, 少年ジャンプ＋, となりのヤングジャンプ, コミックDAYS and similar. Those works
have no ISBN, so the National Diet Library holds nothing for them and no publisher page carries a
reading. Three more (山田恭平, 高橋恭平, 横山陽香) are blocked the other way: NDL holds many
records under those exact names, all of them academics, and none is the manga artist.

Method: `https://ndlsearch.ndl.go.jp/api/opensearch?creator=<name>`, falling back to
`?title=<work>` when the creator index was empty, reading `dcndl:creatorTranscription` beside
`dc:creator`. Every record was checked against the other titles on it before the reading was
accepted. Requests went out as `yurarium/0.1` at ~1.6s intervals. The Agency for Cultural Affairs
Media Arts Database (mediaarts-db.bunka.go.jp) would have been the natural second cataloguer but
it would not accept a connection from here at all, on any path.

Where NDL gave the name in book form it writes the family/given boundary as a comma, reproduced
below as a single space. Where the only record was an electronic-magazine table of contents the
publisher supplies the kana unsplit; those rows say so in the note and the space is placed at the
obvious boundary between the two written elements of the name.

## Found

| name | machine guess | proposed reading | source kind | URL | note |
| --- | --- | --- | --- | --- | --- |
| 宮原 都 | ミヤハラ   ト | ミヤハラ ミヤコ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E5%AE%AE%E5%8E%9F%E9%83%BD | 9 records, 一度だけでも、後悔してます。 (KADOKAWA) and 讐演のアルアビュール (スクウェア・エニックス), all 宮原, 都 → ミヤハラ, ミヤコ. The artist's own X account @aib_miyy carries the display name 宮原都／ミヤハラミヤコ, and おかえりるうちゃん is credited to the same 宮原 都 on となりのヤングジャンプ. |
| 尾羊英 | オ ヒツジ エイ | オヒツジ エイ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E5%B0%BE%E7%BE%8A%E8%8B%B1 | 100 records across three name forms, all オヒツジ: 落ちぶれゼウスと奴隷の子 (朝日新聞出版), 災禍の神は願わない (一迅社), ふつつかな悪女ではございますが (一迅社). One artist; 二人の人魚姫 is their モーニングゼロ 2017年8月期 award piece. |
| 岩渕杏香 | イワブチ キョウカ | イワブチ キョウカ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E5%B2%A9%E6%B8%95%E6%9D%8F%E9%A6%99 | Guess confirmed. Three electronic-magazine records agree: good!アフタヌーン 2023年12号 and 2026年8号 (講談社), ビッグコミックスペリオール 2024年17号 (小学館). Supplied unsplit as イワブチキョウカ. |
| 市川ヒロミ | イチカワ ヒロミ | イチカワ ヒロミ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E5%B8%82%E5%B7%9D%E3%83%92%E3%83%AD%E3%83%9F | Guess confirmed. 6 records for 二兎の除霊師 (集英社), 市川, ヒロミ → イチカワ, ヒロミ. Same artist as モデルチェンジ, which ran in 週刊ヤングジャンプ. |
| 文尾文 | ブンビ ブン | フミオ アヤ | publisher-jp | https://www.shinshokan.co.jp/author/a242048.html | 新書館's author page prints (フミオアヤ). NDL agrees independently on 7 records including the example work 私は君を泣かせたい (白泉社): 文尾, 文 → フミオ, アヤ. |
| 昆布わかめ | コンブ ワカメ | コンブ ワカメ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%98%86%E5%B8%83%E3%82%8F%E3%81%8B%E3%82%81 | Guess confirmed. 46 records, 世界で一番おっぱいが好き！and おっぱい百合アンソロジー (KADOKAWA), 最近雇ったメイドが怪しい (スクウェア・エニックス). |
| 暮みちる | クレ ミチル | クレ ミチル | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%9A%AE%E3%81%BF%E3%81%A1%E3%82%8B | Guess confirmed. Single record, good!アフタヌーン 2026年8号 (講談社), supplied unsplit as クレミチル. Same magazine family as the example work. |
| 木村享平 | キムラ キョウヘイ | キムラ キョウヘイ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%9C%A8%E6%9D%91%E4%BA%AB%E5%B9%B3 | Guess confirmed. The book record is the example work itself: 不思議なゆりこさん (講談社), 木村, 享平 → キムラ, キョウヘイ. Eight 月刊モーニング・ツー issues agree. |
| 杉谷ユカリ | スギタニ ユカリ | スギヤ ユカリ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%9D%89%E8%B0%B7%E3%83%A6%E3%82%AB%E3%83%AA | Only one record: ビッグコミックスペリオール 2025年12号 (小学館), supplied unsplit as スギヤユカリ. Same magazine as the example work 目には目を. Weaker than most rows here, resting on one publisher-supplied string, but the other 27 contributors on that same record are all correct, so the feed is sound. 小学館's own ビッコミ page for 目には目を gives no kana. |
| 柊ゆたか | ヒイラギ ユタカ | ヒイラギ ユタカ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E6%96%B0%E7%B1%B3%E5%A7%89%E5%A6%B9%E3%81%AE%E3%81%B5%E3%81%9F%E3%82%8A%E3%81%94%E3%81%AF%E3%82%93 | Guess confirmed. The example work itself: 新米姉妹のふたりごはん (KADOKAWA), 柊, ゆたか, 1981- → ヒイラギ, ユタカ, 1981-. Strip the birth year. |
| 根岸岳春 | ネギシ タケハル | ネギシ タケハル | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%A0%B9%E5%B2%B8%E5%B2%B3%E6%98%A5 | Guess confirmed. 4 records including the example work ナキノン (ヒーローズ). |
| 桜内美優 | サクラウチ ミユウ | サクライ ミユ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%A1%9C%E5%86%85%E7%BE%8E%E5%84%AA | Two records from two different publishers agree: ＆フラワー 2022年47号 (小学館) and ジュリとエレナの森の相談所 (一二三書房), both サクライミユ, supplied unsplit. サクライ is not the usual reading of 桜内, which is why the guess went wrong, but it is what both cataloguers hold and neither is derived from the other. |
| 橋本ライドン | ハシモト リデオン | ハシモト ライドン | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%A9%8B%E6%9C%AC%E3%83%A9%E3%82%A4%E3%83%89%E3%83%B3 | 5 records including the example work あなたが私を変えたから (KADOKAWA), plus 妹・サブスクリプション (講談社). The guess mangled the katakana that was already there. |
| 沖田さとり | オキダ サトリ | オキタ サトリ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%B2%96%E7%94%B0%E3%81%95%E3%81%A8%E3%82%8A | 7 records, all オキタ: 白線に展転 (講談社) in book form as 沖田 さとり → オキタ サトリ, plus 月刊少年マガジン and ＢＥ・ＬＯＶＥ issues. |
| 沼ちよ子 | ヌマ チヨコ | ヌマ チヨコ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%B2%BC%E3%81%A1%E3%82%88%E5%AD%90 | Guess confirmed. 38 records including the example work ないしょのおふたりさま。(KADOKAWA). |
| 浮足 | ウキアシ | ウキアシ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E6%B5%AE%E8%B6%B3 | Guess confirmed. 終のおもまる (講談社), 浮足 → ウキアシ. One-element pen name, no space. |
| 灯 | アカリ | アカシ | publisher-jp | https://www.kodansha.co.jp/r/comic/product?item=0000363738 | 講談社's product page for the example work prints 著：灯（アカシ）. NDL agrees on the same title: 灯 → アカシ. The stored アカリ was wrong. Same artist as Still Sick. One-element pen name, no space. |
| 田中こめ | タナカ コメ | タナカ コメ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E7%94%B0%E4%B8%AD%E3%81%93%E3%82%81 | Guess confirmed. 25 records, all the example work Killer Twinkle (秋田書店); the collected volume gives 田中, こめ → タナカ, コメ. |
| 白野アキヒロ | シラノ アキヒロ | シラノ アキヒロ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E7%99%BD%E9%87%8E%E3%82%A2%E3%82%AD%E3%83%92%E3%83%AD | Guess confirmed. 10 records including the example work しゅがー・みーつ・がーる! (芳文社) and アマテラスさんはひきこもりたい! (KADOKAWA). |
| 空坂めまう | ソラ サカメ マ ウ | アクサカ メマウ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E7%A9%BA%E5%9D%82%E3%82%81%E3%81%BE%E3%81%86 | Single record, good!アフタヌーン 2025年4号 (講談社), supplied unsplit as アクサカメマウ. The example work 楽園の季節 is this artist's アフタヌーン四季賞 2024冬 藤島康介特別賞 piece, published on コミックDAYS, so the publisher is the same house that supplied the kana. The other 25 contributors on that record are all correct. |
| 竹嶋えく | タケシマ エク | タケシマ エク | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E7%AB%B9%E5%B6%8B%E3%81%88%E3%81%8F | Guess confirmed. 32 records, the example work ささやくように恋を唄う and 君に好きっていわせたい (both 一迅社). |
| 紫のあ | シノア | シノア | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E7%B4%AB%E3%81%AE%E3%81%82 | Guess confirmed. 49 records, the example work この恋を星には願わない (KADOKAWA) and 帰り道 (祥伝社). One-element pen name, no space. |
| 綾瀬れつ | アヤセ レツ | アヤセ レツ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E7%B6%BE%E7%80%AC%E3%82%8C%E3%81%A4 | Guess confirmed. 21 records including the example work ギャングスタガールズ (KADOKAWA). |
| 羽田遼亮 中島零 潮一葉 赤衣丸歩郎 | ハタ リョウ リョウ   ナカジマ レイ   ウシオ イチヨウ   アカギヌマル フ ロウ | ハタ リョウスケ / ナカジマ レイ / ウシオ ヒトハ / アカイ マルボロウ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E5%BF%B5%E9%A1%98%E3%81%AE%E6%82%AA%E5%BD%B9%E4%BB%A4%E5%AC%A2 | All four on one record, the example work itself: 念願の悪役令嬢の身体を手に入れたぞ！（11）(講談社). Each name also checks out separately: 羽田遼亮 on 英雄支配のダークロード (SBクリエイティブ), 中島零 on いぬみみ (白泉社), 赤衣丸歩郎 on 仮面のメイドガイ (富士見書房). Three of the four guesses were wrong. Store as four separate readings if the field allows it. |
| 舟本絵理歌 | マロ | フナモト エリカ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E8%88%9F%E6%9C%AC%E7%B5%B5%E7%90%86%E6%AD%8C | 10 records, 殺し屋Sのゆらぎ and 双影双書 (both 小学館), 舟本, 絵理歌 → フナモト, エリカ. The stored マロ is a different artist's name and should be removed regardless of what replaces it. |
| 苗川采 | ナエカワ サイ | ナエカワ サイ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E8%8B%97%E5%B7%9D%E9%87%87 | Guess confirmed. 142 records, the example work 私を喰べたい、ひとでなし and 後宮一番の悪女 (both KADOKAWA). |
| 茂木ヨモギ | モテギ ヨモギ | モギ ヨモギ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E8%8C%82%E6%9C%A8%E3%83%A8%E3%83%A2%E3%82%AE | 7 records, all モギ: タイフウリリーフ and ドラゴン奉行 (both 小学館). 茂木 takes both readings; this artist uses モギ. The example work 王の由縁 is not in NDL, but the pen name is distinctive enough that a namesake is not a real risk. |
| 葛城かなで | カツラギ カ ナデ | カツラギ カナデ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E8%91%9B%E5%9F%8E%E3%81%8B%E3%81%AA%E3%81%A7 | 26 records. The example work 君となら、明日を歌えるの (KADOKAWA) gives 葛城, かなで → カツラギ, カナデ, and あなたのキスで書きかえて (講談社) agrees. Only the guess's word split was wrong. |
| 藤松盟 | フジマツ メイ | フジマツ メイ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E8%97%A4%E6%9D%BE%E7%9B%9F | Guess confirmed. 71 records, the example work 姉の親友、私の恋人。and おにふたつ (both KADOKAWA). |
| 観乃ふみ | ミ ノ フミ | カンノ フミ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E8%A6%B3%E4%B9%83%E3%81%B5%E3%81%BF | One record, 幼馴染BIG LOVE (KADOKAWA), 観乃, ふみ → カンノ, フミ. The example work 犬も歩けば姫に当たる is a forcs / じるみて title and not in NDL, so this rests on the pen name being the same rare one rather than on a shared record. |
| 辻島もと | ツジシマ モト | ツジシマ モト | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E8%BE%BB%E5%B3%B6%E3%82%82%E3%81%A8 | Guess confirmed. 8 records including the example work やきゅうみようよ! and 天才魔女の魔力枯れ (both 小学館). |
| 郷本 | ゴウモト | ゴウモト | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E5%A4%9C%E3%81%A8%E6%B5%B7 | Guess confirmed. The example work itself: 夜と海 (芳文社), 郷本 → ゴウモト. Also ねこだまり (芳文社) and 破滅の恋人 (白泉社). One-element pen name, no space. |
| 鈴野スケ | スズノ スケ | スズノ スケ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E9%88%B4%E9%87%8E%E3%82%B9%E3%82%B1 | Guess confirmed. 5 records for 冥天レストラン (小学館), supplied unsplit as スズノスケ. |
| 長代ルージュ | ナガシロ ルージュ | ナガシロ ルージュ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E9%95%B7%E4%BB%A3%E3%83%AB%E3%83%BC%E3%82%B8%E3%83%A5 | Guess confirmed. The example work イヴとイヴたち (ジーオーティー) and イヴとイヴ (一迅社). |
| 雪宮ありさ | ユキグウ アリサ | ユキミヤ アリサ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E9%9B%AA%E5%AE%AE%E3%81%82%E3%82%8A%E3%81%95 | 3 records, all the example work 最果てのともだち (芳文社), 雪宮, ありさ → ユキミヤ, アリサ. |
| 鬼無サケル | キナシ サケル | キナシ サケル | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E9%AC%BC%E7%84%A1%E3%82%B5%E3%82%B1%E3%83%AB | Guess confirmed. Both records are the example work 香原さんのふぇちのーと (竹書房). |
| 鰤尾みちる | ブリオ ミチル | ブリオ ミチル | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E9%B0%A4%E5%B0%BE%E3%81%BF%E3%81%A1%E3%82%8B | Guess confirmed. 27 records, the example work バクガタリzzZ and 篠崎くんのメンテ事情 (both KADOKAWA), 神と夢見る嫁の俺 (芳文社). |
| 島 | シマ | シマ | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E3%81%BD%E3%81%8B%E3%81%BD%E3%81%8B%E3%81%9F%E3%81%84%E3%82%8F%E3%82%93%EF%BC%81 | Guess confirmed, but only via the title route: a creator search on 島 returns 2.1 million records and is useless. 32 records for the example work ぽかぽかたいわん！(KADOKAWA), 島 → シマ. One-element pen name, no space. |
| 黒田bb | クロダ bb | クロダ bb | national-library | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E3%82%84%E3%81%97%E3%82%8D%E3%81%AE%E9%AD%94%E7%8E%8B | Guess confirmed. The example work itself: やしろの魔王 (KADOKAWA), 黒田, bb → クロダ, bb. NDL leaves the bb in latin letters; it is not kana and there is no cataloguer anywhere that reads it out, so leave it as-is or drop the row rather than invent ビービー. |

Note on the two rows above that carry a non-NDL URL: 文尾文 and 灯 are the only two names in this
batch where a Japanese publisher prints the reading directly on its own page, so those pages are
cited in preference to the library record even though the library agrees.

## Not found

| name | machine guess | proposed reading | source kind | URL | note |
| --- | --- | --- | --- | --- | --- |
| 南川めぐる | ミナミ カワ メグル | NOT FOUND | — | — | NDL empty on creator and on the example work メイドのデューデ. No publisher page found. |
| 庄司ひろのり | ショウジ ヒロノリ | NOT FOUND | — | — | NDL empty on creator and on クレアちゃん飼育日記. The artist's X account @pekatyo writes the name 庄司 紘徳(ひろのり), which fixes the given name but not the surname, and the pen name is written 庄司ひろのり. The only romaji seen is Hironori Shoji on an English fan-news site, which is not a licensor or publisher, so it is not usable. |
| ○山浩平 | ○ ヤマ コウヘイ | NOT FOUND | — | — | NDL empty on creator and on 天才を描く. The leading ○ is part of the pen name and no source spells it out. |
| ぶり大根 | ブリ ダイコン | NOT FOUND | — | — | NDL empty on creator and on 天瀬ましろはイきたくない！. |
| ノーザンライツ野澤 | ノーザン ライツ ノザワ | NOT FOUND | — | — | NDL empty on creator; a title search on 三年坂 returns 105 unrelated records, none by this artist. |
| 三芳イト | ミヨシ イト | NOT FOUND | — | — | NDL empty on creator and on お嬢様マッチングアプリ. |
| 九淵一真 | キュウ フチ カズマ | NOT FOUND | — | — | NDL empty. 悪魔の口の中 is a 少年ジャンプ＋ award one-shot; the platform page gives no reading. |
| 伊田史郎 | イダ シロウ | NOT FOUND | — | — | NDL empty on creator; a title search on 忘れないでね returns 46 unrelated records. |
| 光莉 | アカリ | NOT FOUND | — | — | NDL holds 光莉 → ヒカリ on 別冊少年マガジン 2026年2月号 (講談社), but the example work 閻魔様のいうとおり is on サンデーうぇぶり (小学館) and that page carries no reading, so there is nothing tying the two together. A single-character pen name is exactly the case where a namesake is most likely, so ヒカリ is recorded here as a lead only and should not be stored. |
| 勇魚とり | イサナ トリ | NOT FOUND | — | — | NDL empty on creator and on 魔法使いの作庭. |
| 友藤みる | トモフジ ミル | NOT FOUND | — | — | NDL empty on creator and on 恋人の下の名前が呼べなくて困ってます. |
| 吉野條二 | ヨシノ ジョウ ニ | NOT FOUND | — | — | NDL empty on creator; a title search on レチタティーヴォ returns 224 classical-music records, none related. |
| 坂南加 | サカミナミ カ | NOT FOUND | — | — | NDL empty on creator and on 神様やめらんない. |
| 壱川ロク | イチ カワ ロク | NOT FOUND | — | — | NDL empty on creator and on おもいあいノ石人間. |
| 夏葉かんな | ナバ カンナ | NOT FOUND | — | — | The one NDL record, サンデーmini 2022年2月号別冊ふろく (小学館), lists 夏葉/つばめ-style contents with no creatorTranscription at all. The example work その矛先、知らぬが愛矢 is not held. |
| 安斎ウト | アンザイ ウト | NOT FOUND | — | — | NDL empty on creator and on のっぽと不登校. |
| 小島りょう | コジマ リョウ | NOT FOUND | — | — | NDL empty on creator and on ほしくずプラネタリウム. |
| 山田恭平 | ヤマダ キョウヘイ | NOT FOUND | — | — | NDL holds 285 records under this name and every one is an academic paper (transformer partial-discharge measurement, polar-region radiation, driving assessment). None carries a transcription and none is the manga artist. The example work 冷厳寺さんは今日からおもちゃ is not held. |
| 御湯川さらり | ゴ ユカワ サラリ | NOT FOUND | — | — | NDL empty on creator and on 封印シールガール ネオ. |
| 春間隆継 | ハルマ タカツグ | NOT FOUND | — | — | NDL empty on creator and on 女子吸血鬼のニカ. No publisher author page found. |
| 朝井いしう | アサイ イシ ウ | NOT FOUND | — | — | NDL empty on creator and on 弓道スケッチ. |
| 東野トシ | トウノ トシ | NOT FOUND | — | — | NDL empty on creator and on マイゾンビシスター. |
| 森あもり | モリ ア モリ | NOT FOUND | — | — | NDL empty on creator; a title search on 神の右手 returns 6 unrelated records. |
| 椎野つばめ | シイノ ツバメ | NOT FOUND | — | — | Two NDL records, サンデーmini 2023年6月号 and 2024年12月号別冊ふろく (小学館), list the name as 椎野/つばめ with no creatorTranscription. The example work つめあと is not held. |
| 横山陽香 | ヨコヤマ ヨウカ | NOT FOUND | — | — | NDL holds 7 records under this name, all medical papers on septic shock and cardiac surgery, none with a transcription. The example work 昼のひもので夜もすがら is not held. |
| 檸檬まるね | レモン マル ネ | NOT FOUND | — | — | NDL empty on creator; a title search on ベリアル returns 229 unrelated records. |
| 気晴すぅ | キ ハラス ゥ | NOT FOUND | — | — | NDL empty on creator and on 中一、五月。. |
| 永瀬ちさと | ナガセ チサト | NOT FOUND | — | — | NDL empty on creator and on ふたり異世界人. |
| 湖山智月 | コザン チゲツ | NOT FOUND | — | — | NDL returns 3 records for this creator string but all are fuzzy matches on other people (白木苺, 平瀬伶, 日之影ソラ). A title search on 雨。のち、晴れ returns 230 unrelated records. |
| 猫柳ユウタ | ネコヤナギ ユウタ | NOT FOUND | — | — | NDL empty on creator and on ガラスノキック. |
| 睦月一 | ムツキ イチ | NOT FOUND | — | — | The one NDL record, サンデーmini 2026年4月号別冊ふろく (小学館), gives the name as 睦月/一 with no creatorTranscription. The example work 湾田さんと蛇ノ目さん is not held. |
| 石川兼心 | イシカワ ケンシン | NOT FOUND | — | — | NDL empty on creator; a title search on 描くこと。 returns 686 unrelated records. The artist has an X account but the display name is written 石川 兼心 with no kana. |
| 花曇パスタ | ハナグモリ パスタ | NOT FOUND | — | — | NDL empty on creator; the 3 records for 私の魔法使い are a Reiki healing series and an unrelated light novel. |
| 藤塚まる | フジツカ マル | NOT FOUND | — | — | NDL empty on creator and on 私達は交際したいのかもしれない. |
| 蝦夷リス | エゾ リス | NOT FOUND | — | — | NDL empty on creator and on あの子が泳いでいた水槽. |
| 西尾 青 | ニシオ   アオ | NOT FOUND | — | — | NDL returns 8 records for 西尾青 and all are haiku collections by 西尾青雨 (ニシオ, セイウ), a different person. The example work ベーズのドアの向こうには is not held. |
| 谷之しぶき | タニノ シブキ | NOT FOUND | — | — | NDL empty on creator; the 3 records for 彼女は悪魔 are unrelated. 彼女は悪魔 runs on となりのヤングジャンプ, whose author pages carry no kana. |
| 青椿トト | アオ ツバキ トト | NOT FOUND | — | — | NDL empty on creator and on ジュリア・イン・ザ・ボックス！. |
| 高橋恭平 | タカハシ キョウヘイ | NOT FOUND | — | — | NDL holds 176 records under this name: geology, fatigue testing, rehabilitation, plus a なにわ男子 idol of the same name. The one transcription present, タカハシ, キョウヘイ, belongs to a 1950s-era physiology thesis author, not the manga artist. The example work とうめいなおとうさん is not held. |
| 黒井真白 | クロイ マッシロ | NOT FOUND | — | — | NDL empty on creator and on キラメキRESTART→. |
