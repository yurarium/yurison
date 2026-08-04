# Author readings, batch 2

Sixty pen names from `authors-2.json`, each carrying a reading produced by the morphological
analyser or back-converted from romaji. Every one was checked against an external source. Nothing
here is inferred from the characters.

**Found 40. Not found 20.**

Of the 40 found, **21 contradict the stored reading** and 19 confirm it. The contradictions include
several that name a different person: 今東ともよ is コンドウ トモヨ and not イマヒガシ, 一七八ハチ is
イナバ ハチ and not イチナナハチ, イマイ悠 is イマイ ハルカ and not イマイ ユウ, 深海紺 is フカウミ コン
and not シンカイ コン, 三本ひより is ミツモト ヒヨリ and not サンポン ヒヨリ.

## Method

The National Diet Library OpenSearch endpoint was the workhorse. Querying `creator=<name>` and
keeping only records whose `dc:creator` matches the pen name exactly gives a `dcndl:creatorTranscription`
for anyone who has a print or electronic book edition. Where the artist has no book, which is the
case for every one of the twenty misses, there is no NDL record at all, and title searches on the
example work return zero as well.

Two other sources carried weight:

- **MADB** (文化庁メディア芸術データベース). The repo already holds a snapshot under `data/source/madb/`
  whose `creator` field is written `名前 / ヨミ`. It resolved 仁科, which NDL does not hold, and it
  independently agreed with NDL on 当麻, 玉崎たま and 鍵穴. The live site at
  `mediaarts-db.bunka.go.jp` was unreachable during this pass: its TLS certificate has expired, so
  MADB citations below point at the id and the local snapshot rather than a page that loads today.
- **The comic-walker author index** (`/api/authors/initial`), which files every KADOKAWA author under
  the first kana of their reading. It gives one kana, never a whole reading, so it never produced a
  FOUND on its own. It did corroborate 今東ともよ (filed under こ, agreeing with NDL's コンドウ and
  refuting the analyser's イマヒガシ) and it refuted the analyser on 出水, filed under い rather than
  the stored シュッスイ.

All requests carried the `yurarium/0.1` User-Agent with roughly 1.6 seconds between hits on a host.
Two sites refused: コミックシーモア returned 404 on its search path, and x.com returned 402 on every
profile fetch, so no X profile could be read directly. DuckDuckGo's HTML endpoint returned an empty
result page for Japanese queries and was abandoned.

## Found

| name | machine guess | proposed reading | source kind | URL | note |
|---|---|---|---|---|---|
| 当麻 | `タイマ` | `トウマ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034463606 | NDL record for あの子とふたりで。, which the corpus also holds under this name. The MADB record for the example work 君のせいなんだから、責任とってよね。 (`data/source/madb/madb-t-fd3353ff9f04.yaml`, M1113550) gives 当麻 / トウマ, so the 百合姫 artist and the オギャー!! artist agree. |
| 鈴木二三江 | `スズキ フミエ` | `スズキ フミエ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032648341 | Confirms the stored reading. 30 exact matches, all スズキ フミエ. |
| みかん氏 | `ミカンシ` | `ミカン ウジ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032057962 | 28 exact matches, all ウジ. 氏 is the given-name half, not a suffix. |
| 守口リョウ | `モリグチ リョウ` | `モリグチ リョウ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I09Y445060000d0000000 | Confirms the guess. Evidence is two ビッグコミックスペリオール issue records; the example work is on 一迅社, so this rests on the pen name being distinctive rather than on a shared imprint. |
| 森島 明子 | `モリシマ   アキコ` | `モリシマ アキコ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I82118216CB000000000X | Confirms the guess; only the doubled space changes. |
| 田口囁一 | `タグチ ショウイチ` | `タグチ ショウイチ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I023846983 | 29 exact matches. MADB agrees (一迅社 / 田口囁一 / イチジンシャ / タグチショウイチ). |
| 仁科 | `ニシナ` | `ニシナ` | national-library (MADB) | https://mediaarts-db.bunka.go.jp/id/M1111274 | MADB record for 春の光に呑まれても (コミック百合姫), snapshot at `data/source/madb/madb-t-8d36b7fa8508.yaml`, creator `仁科 / ニシナ`. NDL holds nothing. comic-walker files 仁科 under に, agreeing. The MADB site's certificate has expired, so the id is citable but the page does not load. |
| 北斗すい | `ホクト スイ` | `ホクト スイ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A14415600000 | Confirms the guess. 30 exact matches. |
| 土屋うさぎ | `ツチヤ ウサギ` | `ツチヤ ウサギ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033858233 | Confirms the guess. |
| 山田hamekon | `ヤマダ hamekon` | `ヤマダ ハメコン` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06A0000000000837681O | The analyser left the latin half untransliterated. 講談社 issue records for 月刊少年マガジン give ヤマダハメコン; the example work is on コミックDAYS, the same publisher. |
| 栗崎きんぐ | `クリサキ キン グ` | `クリサキ キング` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032741531 | The analyser split きんぐ across a word boundary. 22 exact matches. |
| 毒田ペパ子 | `ドクタ ペパコ` | `ドクタ ペパコ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A24688600000 | Confirms the guess. 30 exact matches. |
| 深海 紺 | `シンカイ   コン` | `フカウミ コン` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033045702 | The record is for the example work 恋より青く itself. 深海 here is ふかうみ, not the common しんかい. 8 records, all agreeing. |
| 玉崎たま | `タマザキ タマ` | `タマサキ タマ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029028884 | No rendaku: タマサキ, not タマザキ. MADB agrees (`玉崎たま / タマサキタマ`). |
| 田中火蛾 | `タナカ カ ガ` | `タナカ カガ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06A0000000000947330Y | The analyser split 火蛾 into two words. 講談社 アフタヌーン records; the example work is on コミックDAYS, the same publisher. |
| 竹宮ジン | `タケミヤ ジン` | `タケミヤ ジン` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029431644 | Record is for the example work いとしこいし. 19 records, all agreeing. |
| 蓮尾トウト | `ハスオ トウト` | `ハスオ トウト` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034065398 | Confirms the guess. 20 exact matches. |
| 鍵穴 | `カギアナ` | `カギアナ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033632739 | Confirms the guess. MADB agrees. The book is titled ギャルメイドと悪役令嬢, the web serial 悪役令嬢とギャルメイド. |
| 館山けーた | `タテヤマ ケータ` | `タテヤマ ケータ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033849957 | Confirms the guess. 24 exact matches. |
| うたたね游 | `ウタタ ネ ユウ` | `ウタタネ ユウ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031498115 | Record is for the example work 踊り場にスカートが鳴る. The analyser split うたたね after うたた. |
| ふぁゆ瀬 | `フ ァ ユ セ` | `ファユセ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034452191 | Record is for the example work 竜人ボディガードとお嬢様. One word, no family/given split; the analyser broke the small ぁ off. |
| まめ魚 | `マメ サカナ` | `マメザカナ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I592XXXXXunyakut00111 | Record is for the example work 運命は役に立たない. Rendaku, and written unsegmented in all five records. |
| イマイ悠 | `イマイ ユウ` | `イマイ ハルカ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033378875 | Record is for the example work 下僕さんと主ちゃんの日常. 悠 is はるか here, not ゆう. 10 records agree. |
| マポロ3号 | `マポロ 3 ゴウ` | `マポロ サンゴウ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033348144 | NDL writes the transcription `マポロ 3ゴウ`, keeping the digit. 3号 is さんごう and takes no other reading, but if the pipeline would rather not expand a digit, store NDL's literal form. 13 records agree. |
| 一七八ハチ | `イチナナハチ ハチ` | `イナバ ハチ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029940939 | 一七八 is the surname いなば, not the digits read out. 8 records agree. |
| 七福あくび | `シチフク アクビ` | `シチフク アクビ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034214601 | Confirms the guess. |
| 三本ひより | `サンポン ヒヨリ` | `ミツモト ヒヨリ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032437421 | 三本 is the surname みつもと, not the counter さんぼん. |
| 亀島潤斗 | `カメジマ ジュン ト` | `カメジマ ジュント` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I08X10000000064693500 | The analyser split 潤斗. 30 exact matches, all カメジマジュント. |
| 井上和郎 | `イノウエ カズオ` | `イノウエ カズロウ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I000008021801 | 和郎 is かずろう. Confirmed across あいこら and 美鳥の日々, both by the 小学館 artist who also drew the example work on サンデーうぇぶり. |
| 今東　ともよ | `イマヒガシ 　 トモ ヨ` | `コンドウ トモヨ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033862871 | Record is for the example work 午前二時は食卓で. 今東 is こんどう. comic-walker files this author under こ, agreeing. The stored reading names nobody. |
| 住咲ゆづな | `ジュウ サキ ユヅナ` | `スミサキ ユズナ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029274404 | 住 is すみ, and NDL writes the given name ユズナ rather than ユヅナ. |
| 北尾タキ | `キタオ タキ` | `キタオ タキ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033718089 | Record is for the example work 平民の私ですが公爵令嬢様をたぶらかして生きています. Confirms the guess. |
| 千葉らき | `チバ ラキ` | `チバ ラキ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033748117 | Record is for the example work シャイなあの子に懐かれたい. Confirms the guess. |
| 博（ひろ） | `ヒロシ` | `ヒロ` | platform | https://tonarinoyj.jp/episode/12207421983966650782 | となりのヤングジャンプ prints the byline with the artist's own furigana in the name itself: 博（ひろ）. The parenthetical is the reading. The analyser read the kanji alone and produced ヒロシ. |
| 吉沢タクマ | `ヨシザワ タクマ` | `ヨシザワ タクマ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I09Y443040000d0000000 | Confirms the guess. Single ビッグコミックスペリオール issue record against a KADOKAWA example work, so this is the thinnest of the confirmations; the pen name is distinctive enough to carry it. |
| 夏村東和 | `ナツ ムラ トウワ` | `ナツムラ トワ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034543920 | Record is for the example work 腹割るウチらの秘密ごと!. 東和 is とわ, not とうわ. |
| 夏鈴糖 | `カリントウ` | `カリントウ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032807842 | Confirms the back-conversion. One word, five records agreeing. |
| 大刃堂寿 | `オオバ ドウズ` | `オオバ ドウズ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032539213 | Confirms the back-conversion. Single record. |
| 大石日々 | `オオイシ ヒビ` | `オオイシ ヒビ` | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033686326 | Record is for the example work よくばれ!人間さん. **Sources conflict.** NDL's own cataloguing gives オオイシ, ヒビ on all five book records (小学館 and 双葉社, including the example work); the seventeen electronic-magazine records supplied by the distributor give オオイシビビ. Taking the catalogue over the distributor, which also happens to confirm the stored reading. Worth a second look if it matters. |
| 安房さとる | `アボウ サトル` | `アボウ サトル` | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A23751100000 | Record is for the example work スロー・ステップ！. Confirms the back-conversion. 30 exact matches. |

## Not found

Twenty names. Every one of them is a web-only artist with no book edition, which is why the National
Diet Library holds nothing: `creator=`, `any=` and a `title=` search on the example work all returned
zero exact matches for each. The bookstore route dies for the same reason, since a shop cannot list a
book that does not exist. Serving no furigana for these is the right outcome.

| name | machine guess | what was checked |
|---|---|---|
| ささた汐 | `ササタ シオ` | NDL by creator, by any-field, and by the example title かわいい親友の落とし方: all zero. The work is a ten-page one-shot on となりのヤングジャンプ with no volume. No artist page found. |
| 庄司ひろのり | `ショウジ ヒロノリ` | NDL zero on all three routes. comic-walker files the author under し, which is consistent with ショウジ but gives only the first kana, so it cannot settle the given name. |
| 相模 | `サガミ` | NDL creator search returns 16,694 results, none an exact match on the bare pen name; the hits are 相模原市 institutions and researchers with 相模 in a surname. Title search on 知らない海を教えて is zero. |
| 純玲 | `スミレ` | NDL zero exact; the 35 hits are academics whose given name is 純玲. comic-walker files the author under す, consistent with スミレ but only the first kana. Not enough. |
| のぴやか梢 | `ノ ピ ヤ カ コズエ` | NDL zero. The only 多重夢 record is an unrelated 1980s dōjin collection. The work is a コミックゼノン one-shot. |
| ナムラ瓶中 | `ナムラ ビンチュウ` | NDL zero on creator, any-field and 一条ヒヨコはピアノだけ. Debut one-shot on 少年ジャンプ+, no volume, no artist page located. |
| 上田さかひら | `ウエダサ カ ヒラ` | NDL zero on all routes. The analyser also mis-split the surname, gluing さ to 上田. |
| 乃田ユウキ | `ノダ ユウキ` | NDL zero on all routes. |
| 出水 | `シュッスイ` | NDL creator search returns 3,126 results, none an exact match on the bare name. comic-walker files this author under い, which rules the stored シュッスイ out but does not establish the reading. Recommend clearing the furigana rather than keeping the guess. |
| 伊田史郎 | `イダ シロウ` | NDL zero on all routes. |
| 原川ユキ | `ハラカワ ユキ` | NDL zero on creator, any-field and 恋の焦点. |
| 古川拓 | `フルカワ タク` | NDL's two exact creator matches are engineering and labour-law papers by a different 古川拓, and neither carries a transcription. Title search on もらったもの is zero. |
| 史織 | `シオリ` | NDL creator search returns 1,275 results, none an exact match on the bare name; all are researchers whose given name is 史織. |
| 吉野條二 | `ヨシノ ジョウ ニ` | NDL zero on creator and any-field. The 224 hits on レチタティーヴォ are all classical-music recordings. |
| 園河ソノ | `エンガ ソノ` | NDL zero on all routes. A community database (manba) lists the artist but carries no reading. |
| 坂城 | `サカキ` | NDL creator search returns 1,129 results, none an exact match; the hits are 坂城町 (Nagano) municipal publications. |
| 塩士標 | `シオシ ヒョウ` | NDL zero on all routes. The artist's X handle is `@siozihyo`, which maps cluster-for-cluster onto 塩-士-標 and points at しおじひょう rather than the stored シオシ. That is a lead worth recording, but x.com returns 402 to any fetch so the profile could not be read, and the handle leaves ひょ against ひょう unresolved. Not enough to publish. |
| 壱弎ハルヒト | `イチ サン ハルヒト` | NDL zero on creator, any-field and 其れの手も借りるほど. No artist page located. |
| 妻木都 | `ムキ ト` | NDL zero on all routes; honto and bookwalker return no book. comic-walker files the author under つ, which refutes the stored ムキ (the surname is つまき) but leaves 都 unresolved. Recommend clearing the furigana. |
| 光莉 | `アカリ` | NDL has one exact creator match, ヒカリ, on a 別冊少年マガジン issue (講談社). The corpus work 閻魔様のいうとおり is on サンデーうぇぶり (小学館), and 光莉 is a short enough pen name that two artists can plausibly hold it. Refusing to carry a 講談社 reading across to a 小学館 artist on no other evidence. |

## Leads for a later pass

- The MADB live site is worth retrying once its certificate is renewed. Its coverage of 百合姫 and
  other 一迅社 imprints resolved 仁科 where NDL could not, and it may reach a few more of the twenty.
- The comic-walker author index gives a reliable first kana for every KADOKAWA author. It is not a
  reading on its own, but as a cross-check it caught the 今東ともよ fault independently and would
  make a cheap invariant against future analyser output.
