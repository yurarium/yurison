# Author readings, credit-line round 2

71 names checked. 61 readings found, 10 not found.

Every name in this batch appeared only inside a multi-person credit line, so the stored guesses were
mis-segmented as well as unsourced. 23 of the 61 found differ from the stored guess in kana and not
merely in spacing. The worst were 今安, stored イマヤス, which is ジンアン; 娘太丸, stored ムスメ
タマル, which is コタマル; 銃爺, stored ジュウヤ, which is ガンジイ; 志瑞祐, stored ココロザシ ズイ
ユウ, which is シミズ ユウ; りりうら世都, stored リ リウラ セツ, which is リリウラ ヨミヤ; and
宮原都, stored ミヤハラ ト, which is ミヤハラ ミヤコ. Several others were surname readings the
guesser picked wrongly (南高 ナンコウ for ナダカ, 新城 シンシロ for シンジョウ, 佐島 サジマ for
サトウ, 王月 オウ ゲツヨウ for オウズキ ヨウ, 後谷戸 アトタニト for ウシロヤト, 蛙田 カエダ for
カエルダ, 錫江 スズコウ for スズエ, 紗嶋 シャシマ for サジマ, 耳式 ジシキ for ミミシキ, 朝霧咲
アサギリ サキ for アサギリ サク, 潮一葉 ウシオ イチヨウ for ウシオ ヒトハ, 月夜涙 ツキヨ ナミダ
for ツキヨ ルイ). The remaining 38 were right in kana and wrong only about where one name ends, the
break falling inside a single unit (恥谷きゆう ハジ タニ キユ ウ, 花宮みぃ ハナミヤミ ィ, 破賀
ミチル ハ ガ ミチル, 彩乃浦助 アヤノ ウラ スケ, 倫理きよ リンリキ ヨ, 和ふー ワ フー).

One row is not a furigana problem at all. 角川青羽 in the 入味 credit is 角川青羽（上海）文化創意
有限公司, the Shanghai KADOKAWA company that produced the edition, not a person. The National Diet
Library records it as a corporate body with no transcription. The stored カドカワ アオバ should be
dropped rather than replaced.

The 10 not found are artists whose only credits are web serials or one-shots on 少年ジャンプ＋,
サンデーうぇぶり, カドコミ, チャンピオンクロス and WEBコミックガンマ, plus three who are the
character designer or scenario supervisor on someone else's book and so never carry an NDL heading
of their own. Their works have no ISBN, and the platform pages print the pen name without a reading.
餡こたく is the clearest case: NDL holds ステラ・ステップ but lists only りんご水 and 林星悟 on it.

Method: `https://ndlsearch.ndl.go.jp/api/opensearch?creator=<name>`, falling back to `?title=<work>`
and `?any=<name>`, reading `dcndl:creatorTranscription` beside `dc:creator` and pairing the two
element lists positionally. That pairing is what resolved 今安 and 伍長, neither of whom has a book
under their own heading; both fell out of a KADOKAWA volume record whose two creators and two
transcriptions line up one to one. NDL writes the family/given boundary as a comma, replaced below
with a single space. Where NDL supplies no boundary but the written name splits plainly into a kanji
surname and a kana given name, the space is noted as coming from the written name rather than from
the record.

| name | machine guess | proposed reading | source kind | URL | note |
|---|---|---|---|---|---|
| 塩こうじ | シオコウジ | シオコウジ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784040764801 | record is the example work; NDL treats it as one unit, no boundary |
| 羽柴実里 | ハシバ ミサト | ハシバ ミサト | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I09D129210000d0000000 | record is the example work, paired with zinbei ジンベエ; space from the written name |
| 南高春告 | ナンコウ ハルツゲ | ナダカ ハルツグ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031217131 | record is the example work; surname and given name both misread by the guesser |
| 渡辺零 | ワタナベ レイ | ワタナベ レイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032542328 | heading is from きみと観たいレースがある; the same writer is credited 原作 on サバーキ |
| 藤川よつ葉 | フジカワ ヨツハ | フジカワ ヨツバ | author | https://lit.link/en/fujikawayotsuba | own link page and X handle both romanise Fujikawa; NDL's authority heading says フジガワ, so the author's own form is preferred |
| りんご水 | リンゴスイ | リンゴスイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034392235 | record is the example work; one unit |
| 餡こたく | アンコタク | NOT FOUND | | | NDL holds ステラ・ステップ but credits only りんご水 and 林星悟; creator, title and any searches all empty; pixiv and cmoa print the name without kana |
| 南部くまこ | ナンブ クマコ | ナンブ クマコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000136-I1970304959855939592 | heading is from KADOKAWA children's titles, matched on the pen name only |
| 波多ヒロ | ハタ ヒロ | ハタ ヒロ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784041175651 | record is volume 2 of the example work |
| 不和二亜 | フワ ニ ア | NOT FOUND | | | creator, title and any searches all return nothing; the work is a web serial with no ISBN |
| 大鷹シン | オオタカ シン | オオタカ シン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034353215 | record is the example work |
| 彩乃浦助 | アヤノ ウラ スケ | アヤノ ウラスケ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I08X10000000042395500 | record is the example work; NDL's heading 彩乃, 浦助 puts the boundary after 彩乃 |
| 星崎崑 | ホシザキ コン | ホシザキ コン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031647512 | heading is from the light novels; same author writes the example work |
| 時任せつな | トキトウ セツナ | トキトウ セツナ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784046603739 | record is volume 2 of the example work |
| 花宮みぃ | ハナミヤミ ィ | ハナミヤ ミィ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034681750 | heading is from 芳文社 titles, matched on the pen name only |
| 銃爺 | ジュウヤ | ガンジイ | publisher-jp | https://shogakukan-comic.jp/author?cd=15957 | Shogakukan's author page for the example work prints ガンジイ; NDL agrees at R100000137-I09D151700000d0000000, though its magazine records say ガンジー |
| 恥谷きゆう | ハジ タニ キユ ウ | ハジタニ キユウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784049722307 | record is the example work |
| 今安 | イマヤス | ジンアン | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784046857583 | record is the example work; creators 小畠　泪 and 今安 pair with オバタ　ルイ and ジンアン. Creator search returns only academic namesakes |
| デス山ハナ子 | デスサン ハナコ | デスヤマ ハナコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784048119917 | record is volume 3 of the example work |
| 和ふー | ワ フー | ワフー | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034363049 | record is the example work; NDL gives no boundary |
| 五色安未 | ゴシキ アミ | ゴシキ アミ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033907724 | record is the example work |
| 伍長 | ゴチョウ | ゴチョウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06A0000000001037022S | volume 4 of the example series; creators 空山　トキ and 伍長 pair with ソラヤマトキ and ゴチョウ |
| 右腹 | ミギハラ | ミギハラ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033957935 | record is the example work; one unit |
| 新城一 | シンシロ イチ | シンジョウ ハジメ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I06Z0139915510001000I | magazine and 分冊版 records give シンジョウハジメ; NDL's authority heading 新城, 一 fixes the boundary |
| 久賀　フーナ | クカ 　 フーナ | クガ フーナ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784824018199 | 26 records under クガフーナ; boundary is the full-width space already in the credit |
| 坂南加 | サカミナミ カ | NOT FOUND | | | creator, any and title=姉妹傭兵 all empty; the work is on カドコミ only and the KADOKAWA product page omits the artist |
| 能代リョウ | ノシロ リョウ | ノシロ リョウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034011848 | record is the example work |
| 糀もろみ | コウジ モロミ | コウジ モロミ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033905579 | record is the example work |
| さわやか鮫肌 | サワヤカ サメハダ | サワヤカサメハダ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A23774700000 | record is the example work; NDL gives no boundary |
| 破賀ミチル | ハ ガ ミチル | ハガ ミチル | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034363229 | record is the example work |
| りんご飴サード | リンゴ アメ サード | リンゴアメ サード | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034666209 | record is the example work; NDL's own spacing |
| 志瑞祐 | ココロザシ ズイ ユウ | シミズ ユウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029925165 | 24 records under the heading 志瑞, 祐; the author's X handle @shimizuMFJ agrees |
| 王月よう | オウ ゲツヨウ | オウズキ ヨウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032482150 | record is the example work |
| 煮ル果実 | ニ ル カジツ | ニル カジツ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034663002 | record is the example work; NDL's own spacing |
| 両備イエリ | リョウビ イエリ | NOT FOUND | | | creator, any and title=傷の女 all fail to place the name; サンデーうぇぶり only, no ISBN |
| 佐島勤 | サジマ ツトム | サトウ ツトム | national-library | https://ndlsearch.ndl.go.jp/books/R100000136-I1970867909773172271 | 22 records under 佐島, 勤 including the example series |
| 陣ノ内康暉 | ジンノウチ コウキ | ジンノウチ コウキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034589307 | record is the example work |
| 川上しをん | カワカミ シヲン | カワカミ シオン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034566690 | the national bibliography record for the example work reads シオン; KADOKAWA's own 分冊版 metadata supplies カワカミシヲン, kept here as a variant |
| 倫理きよ | リンリキ ヨ | リンリ キヨ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029147998 | transcription is on an earlier title under the same heading 倫理, きよ; the example work carries the heading with the field blank |
| 潮一葉 | ウシオ イチヨウ | ウシオ ヒトハ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784065449530 | record is volume 11 of the example work |
| 日之下あかめ | ヒ ノ シタ アカメ | ヒノシタ アカメ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029476413 | heading is from エーゲ海を渡る花たち and 河畔の街のセリーヌ |
| エストレーヤ★彡 | エストレーヤ ★ キゴウ | NOT FOUND | | | nothing under creator, any, title=シュナイダーラリー or title=シュナイダー・ラリー; cmoa and ebookjapan print the name without kana. The ★彡 is decoration and carries no reading, so the stored キゴウ is wrong whatever the rest turns out to be |
| 米田タロウ | ヨネダ タロウ | ヨネダ タロウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034545724 | record is the example work |
| 小野亮汰 | オノ リョウタ | NOT FOUND | | | creator, any and title=推し活バスケ all empty; 少年ジャンプ＋ one-shot with no ISBN |
| 柚子桃 | ユズ モモ | ユズモモ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033260709 | record is the example work; NDL treats it as one unit |
| 耳式 | ジ シキ | ミミシキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A22496500000 | record is the example work; 30 records agree |
| 田中まさみ | タナカ マサミ | タナカ マサミ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A16587000000 | 22 records for the example series give タナカマサミ; space from the written name |
| 月夜 涙 | ツキヨ   ナミダ | ツキヨ ルイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I030353242 | 29 records under 月夜, 涙 |
| 黒イ森 | クロ イ モリ | クロイ モリ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032813276 | record is the example work; NDL's own spacing |
| あらおし悠 | アラ オシ ユウ | アラオシ ユウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I000011266393 | 28 records under あらおし, 悠 |
| 森山大輔 | モリヤマ ダイスケ | モリヤマ ダイスケ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031414283 | heading 森山, 大輔, 1971-; birth year dropped from the reading |
| 紗嶋 | シャ シマ | サジマ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034771830 | record is the example work; one unit |
| 後谷戸隆 | アト タニト タカシ | ウシロヤト タカシ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032035379 | heading 後谷戸, 隆, 1986-; birth year dropped from the reading |
| 錫江 | スズコウ | スズエ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A23082100000 | 26 records for the example work; one unit |
| 新島あん | ニイジマ アン | ニイジマ アン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032756864 | record is the example work |
| 動画投稿少女 | ドウガ トウコウ ショウジョ | ドウガトウコウショウジョ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033567569 | a collective pseudonym for the anime committee, not a personal name; NDL spaces it as three words but there is no family/given boundary to mark |
| 娘太丸 | ムスメ タマル | コタマル | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I023585526 | 11 records including 結城友奈は勇者である娘太丸アートワークス, the same artist as the example work; one unit |
| 朝霧咲 | アサギリ サキ | アサギリ サク | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033918778 | record is the example work; heading 朝霧, 咲, 2004- |
| 黒田所 | クロダショ | NOT FOUND | | | creator, any and title=結ばれる日 all fail to place the name; チャンピオンクロス one-shot with no ISBN |
| 桐原のん | キリハラ ノン | キリハラ ノン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033430756 | heading from other titles, matched on the pen name only; the example work is a ジャンプTOON one-shot |
| サンクス仮面 | サンクス カメン | サンクス カメン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032987553 | heading from サトム・フォーリンラブ; NDL's own spacing |
| 爽穂詩三駈 | アキオ シ サン ク | NOT FOUND | | | creator, any and a 98-record sweep of ジャンプGIGA issues all fail to place the name |
| 蛙田アメコ | カエダ アメコ | カエルダ アメコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I2530000D0048560050A1 | 14 records give カエルダアメコ; space from the written name |
| 角川青羽 | カドカワ アオバ | NOT FOUND | | https://ndlsearch.ndl.go.jp/books/R100000002-I032867042 | not a person. The 入味 credit is 角川青羽（上海）文化創意有限公司, recorded by NDL as a corporate body with the transcription field empty. The stored reading should be dropped, not replaced |
| 田中天 | タナカ タカシ | タナカ タカシ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I000009949153 | heading 田中, 天, 1977-, the tabletop RPG writer behind ナイトウィザード and アリアンロッド; birth year dropped |
| 浅野龍哉 | アサノ タツヤ | アサノ タツヤ | national-library | https://ndlsearch.ndl.go.jp/books/R100000136-I1971993809756396736 | heading from 指輪物語 浅野龍哉作品集, the artist who also works with 大塚英志 |
| 阿羅本景 | アラ モトカゲ | アラモト ケイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031186031 | record is the example work; the author's X handle @aramotokei agrees |
| 桜木さやか | サクラギ サヤカ | NOT FOUND | | | creator and title=アサルトリリィ League of Gardens both fail to place the name; credited as scenario supervisor, so no NDL heading of their own |
| 宮原都 | ミヤハラ ト | ミヤハラ ミヤコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032593581 | the example work carries the heading 宮原, 都, whose transcription is on 一度だけでも、後悔してます。 |
| 菅原こゆび | スガワラ コユビ | スガワラ コユビ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031381125 | record is the example work |
| りりうら世都 | リ リウラ セツ | リリウラ ヨミヤ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031717560 | nine records for the example work under りりうら, 世都 |
