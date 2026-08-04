# Author readings, credit-line round 1

72 names checked. 61 readings found, 11 not found.

Of the 61 found, 33 differ from the machine guess in kana rather than merely in spacing. Another
seven were right in kana but split in the wrong place, which is the failure this batch was assembled
to catch: 柚原もけ came out ユハラ モ ケ and is ユズハラ モケ, 猫屋敷ぷしお came out ネコヤシキプ シオ
and is ネコヤシキ プシオ, 遠野めざ ran together as トオノメザ and is トオノ メザ.

The worst guesses were whole-name inventions. 狐印 was stored キツネ シルシ and reads コイン. 志田
was stored シダ and reads サネダ. 洲央 was stored シマ ヒロシ and reads スオウ. 我孫子楽人 was stored
アビコ ガクジン and reads アビコ カナト. 羽流木はない was stored ハル キ ワ ナイ and reads
ワルギ ハナイ. 二三　夏一 was stored ニサン カイチ and reads フミ ナツイチ. 朱白あおい was stored
シュ ハク アオイ and reads アカシロ アオイ. 尾花沢軒栄 was stored オバナザワケン サカエ and reads
オバナザワ ケンエイ.

Three entries are not people and need a decision beyond furigana. 「１冊目：叔母さんは神絵師」 is the
first chapter title of 破賀ミチル's 新刊100億冊ください, and 「１．月と太陽の日々」 is a chapter title
inside 陣ノ内康暉's GURU. Both were swept into the credit field by the parser and should be deleted
rather than given a reading. 「真夜中ぱんチ」製作委員会 is a production committee, 東方Project is a
franchise and 電撃G'sマガジン is a magazine; all three do carry catalogued readings, listed below, but
they are organisations rather than artists.

Two readings conflict between sources and are flagged in the notes: 羽流木はない, where NDL's own
book records say ワルギ ワナイ although the given name is already written in kana as はない, and
矢立肇, where NDL consistently says ヤダテ while general usage says ヤタテ.

Method: `https://ndlsearch.ndl.go.jp/api/opensearch?creator=<name>`, falling back to `?title=<work>`
when the creator index was empty, reading `dcndl:creatorTranscription` beside `dc:creator`. Pairing
the two element lists positionally is what carried this round: KADOKAWA, 講談社 and ヒーローズ
e-book records list every person on a multi-person credit line with one transcription each in the
same order, so a writer or character designer with no book of their own still yields a catalogued
reading from a colleague's volume. That is how 志田, 深津, 桜河ゆう, 珠樹みつね, 朱白あおい,
柳井伸彦, 羽田遼亮 and 猫屋敷ぷしお were resolved. Every record was checked against the other titles
on it to rule out a namesake; 竹内和成 and 福井遥香 were rejected on exactly that ground, since their
NDL hits are an orthopaedic surgeon and an archaeologist. Requests went out as `yurarium/0.1` at
roughly 1.7s apart.

Where the same person appears with two NDL spellings, NDL's own catalogue records (R100000002)
normalise づ to ズ and ぢ to ジ while publisher-supplied e-book records (R100000137) keep them. The
proposals below take the publisher form for 望月けい, 神無月羽兎 and 猫屋敷ぷしお and say so in the
note.

| name | machine guess | proposed reading | source kind | URL | note |
|---|---|---|---|---|---|
| 鴉ぴえろ | カラス ピエロ | カラス ピエロ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784040764863 | Guess was already right. 87 other records give the same kana unsegmented as カラスピエロ. |
| 花ヶ田 | ハナ ガ タ | ハナガタ | author | https://www.pixiv.net/en/artworks/140699927 | Artist's own pixiv account is hanagata. One unit, no family/given boundary. NDL's 創成魔法の再現者 record agrees (https://ndlsearch.ndl.go.jp/books/R100000137-I9784824017659); NDL's 私の推しは悪役令嬢。連載版 records say ハナケダ and are wrong. |
| 夜の羊雲 | ヨル ノ ヒツジグモ | ヨルノヒツジグモ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A22627800000 | One unit, no boundary. NDL's book record writes it word-spaced as ヨル ノ ヒツジグモ. |
| 遠井音 | トウイ オト | NOT FOUND | | | NDL creator and title 春の埋み火 both empty; the story ran in コミック百合姫 2026年4月号 with no book. 一迅プラス author listing prints no kana. The artist's X handle @oto_toi looks like a pun on おととい but that is not a stated reading. |
| 古田朋大 | フルタ トモヒロ | フルタ トモヒロ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033374588 | Guess was right. Namesake ceramics researcher also present in NDL with no reading. |
| 柚原もけ | ユハラ モ ケ | ユズハラ モケ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I030715643 | 安達としまむら公式コミックアンソロジー, the example work. |
| 林星悟 | ハヤシ ホシ サトル | ハヤシ ショウゴ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032588339 | ステラ・ステップ, the example work. |
| 西馬ごめゆき | サイバ ゴメ ユキ | ニシマ ゴメユキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033445772 | Found by title; the creator index files this artist with a birth-year suffix. |
| 春木やちか | ハルキ ヤチ カ | NOT FOUND | | | NDL creator and title この湯で、あなたと both empty. Only trace is a カドコミ search page, which prints no kana. |
| 岡野く仔 | オカノ クコ | オカノ クコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034323842 | Guess was right. |
| 南方純 | ミナカタ ジュン | ミナカタ スナオ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I030190539 | The example work itself, THE COMIC edition, マイクロマガジン社. |
| 遠野めざ | トオノメザ | トオノ メザ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033474587 | バカ女26時, the example work. Kana were right, the boundary was missing. |
| 狐印 | キツネ シルシ | コイン | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784824017963 | The example work's volume 2, so identity is direct rather than inferred from 防振り. |
| 志田 | シダ | サネダ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A24329800000 | Positional pairing on the example work: ばたっち / 星崎崑 / 志田 to バタッチ / ホシザキコン / サネダ. |
| 桃田ロウ | モモタ ロウ | モモタ ロウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033967083 | Guess was right. |
| 笹塔五郎 | ササ トウ ゴロウ | ササ トウゴロウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031722989 | Kana were right, the boundary was in the wrong place. |
| 珠樹みつね | タマキ ミツネ | タマキ ミツネ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784049722307 | Guess was right. Positional pairing on the example work's volume 1. |
| 桜河ゆう | サクラガワ ユウ | オウカワ ユウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784049722307 | Same record, third position: 桜河　ゆう to オウカワ　ユウ. |
| 東方Project | トウホウ Project | トウホウプロジェクト | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A13099200000 | A franchise credited as originator, not a person. |
| 神無月羽兎 | カンナヅキワ ウサギ | カンナヅキ ハト | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A18437800000 | NDL's own book records normalise this to カンナズキ, ハト. |
| 空山トキ | ソラヤマ トキ | ソラヤマ トキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033648981 | Guess was right. |
| 泉乃せん | ミズノ セン | イズミノ セン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033395195 | Confirmed again by the 月刊少年シリウス issue records that carry the example work. |
| 小林湖底 | コバヤシ コテイ | コバヤシ コテイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000001-I11213366710 | Guess was right. ひきこまり吸血姫, the example series. |
| 羽田 宇佐 | ハタ   ウサ | ハネダ ウサ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032625176 | 週に一度クラスメイトを買う話, the example work. Not the same surname reading as 羽田遼亮. |
| 二三　夏一 | ニサン 　 カイチ | フミ ナツイチ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034353142 | わたくし、負けませんので。, the example work. |
| 絵本奈央 | エモト ナオ | エモト ナオ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I028081464 | Guess was right. |
| 三河ごーすと | ミカワ ゴー ストッ | ミカワ ゴースト | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I023582167 | |
| 朱白あおい | シュ ハク アオイ | アカシロ アオイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784868052142 | The example work; positional pairing across all four credited names. |
| 柳井伸彦 | ヤナイ ノブヒコ | ヤナイ ノブヒコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784868052142 | Guess was right. Fourth position on the same record. |
| 青乃下 | アオ ノ シタ | アオノ シモ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034041075 | 私の推しは悪役令嬢。, the example work, 一迅社. |
| １冊目：叔母さんは神絵師 | イチサツメ ： オバサン ワ カミエシ | NOT FOUND | | | Not a person. This is the first chapter title of 新刊100億冊ください; NDL credits that book to 破賀ミチル alone (https://ndlsearch.ndl.go.jp/books/R100000002-I034363229). Delete the entry rather than give it furigana. |
| 川田暁生 | カワタ アキオ | カワダ アキオ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I030631814 | The example work's e-book records agree (カワダアキオ). |
| 本間リョウタ | ホンマ リョウタ | ホンマ リョウタ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033562857 | Guess was right. T.Tラバーズ。, the example work. |
| 深津 | フカツ | フカツ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A25950900000 | Guess was right. Positional pairing on 紗痲 Fallin' Jail【分冊版】1: 深津 / 煮ル果実 / WOOMA to フカツ / ニルカジツ / ウーマ. |
| ぴよぴよ丸 | ピヨピヨ マル | ピヨピヨマル | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034235006 | One unit, no boundary. ウは宇宙ヤバイのウ!, the example work. |
| 竹内和成 | タケウチ カズナリ | NOT FOUND | | | NDL creator returns 50+ records, all of them an orthopaedic surgeon of the same name, and none with a transcription. Title 傷の女 finds only unrelated works; the piece ran on サンデーうぇぶり with no book and no kana. |
| 裏海マユ | ウラカイ マユ | リガイ マユ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032575813 | お父さんが早く死にますように。, ファンギルド. Corroborated by the artist's own X handle @whiterigai. |
| １．月と太陽の日々 | イチ． ツキ ト タイヨウ ノ ヒビ | NOT FOUND | | | Not a person. A chapter title inside 陣ノ内康暉's GURU that the parser swept into the credit field. Delete the entry. |
| 猫屋敷ぷしお | ネコヤシキプ シオ | ネコヤシキ プシオ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784049523676 | Positional pairing: 入間　人間 / 猫屋敷　ぷしお to イルマ　ヒトマ / ネコヤシキ　プシオ. |
| 羽田遼亮 | ハタ リョウ リョウ | ハタ リョウスケ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I9784065449530 | The example work, volume 11; all four credited names pair cleanly. |
| 蔵王大志 | ザオウ タイシ | ザオウ タイシ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031725994 | Guess was right. |
| 望月けい | モチヅキ ケイ | モチヅキ ケイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A16789600000 | Guess was right. Identity confirmed by the 人間よ強欲であれ : 望月けい画集 record, which spells it モチズキ, ケイ under NDL's づ normalisation. |
| 七橋楽 | シチ ハシガク | ナナハシ ラク | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034145587 | 幼馴染は、にゃあと鳴いてスカートのなか, the example work. |
| 福井遥香 | フクイ ハルカ | NOT FOUND | | | NDL creator returns three records, all an archaeologist writing about roof tiles in Nagasaki. Title Queentopia Project empty; a タテスク vertical-scroll title with no book. |
| 小野正太郎 | オノ ショウタロウ | NOT FOUND | | | NDL creator returns one record, a genealogy with no creator field. Title 推し活バスケ empty. |
| 司馬漬け | シバツケ | シバズケ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033260709 | ふたり暮らしのおとりよせ日和, the example work. One unit, no boundary. |
| ピザ萬 | ピザ ヨロズ | ピザマン | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A16587000000 | The example work, chapter 1. One unit, no boundary. |
| 犬甘あんず | イヌカイ アンズ | イヌカイ アンズ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033161239 | Guess was right. The example work. |
| 島崎無印 | シマザキ ムジルシ | シマザキ ムジルシ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032813276 | Guess was right. エリオと電気人形, the example work. |
| 鈴音れな | スズネ レナ | スズノネ レナ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031637553 | 百合ラブスレイブ, the example work. |
| 倉田英之 | クラタ ヒデユキ | クラタ ヒデユキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A22059600000 | Guess was right. NOMADS ノーマッズ; the creator index also holds several unrelated academics under these characters. |
| 洲央 | シマ ヒロシ | スオウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033632738 | 崖っぷち令嬢は黒騎士様を惚れさせたい!, the example work, 一迅社. One unit, no boundary. |
| 恵茂田喜々 | エモタ キキ | エモダ キキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033318653 | 君のためのカーテンコール, the example work. |
| 我孫子楽人 | アビコ ガクジン | アビコ カナト | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033630105 | きみの絶滅する前に, 講談社, the artist's only catalogued book. A モーニング 2026年21号 issue record gives the same reading. |
| 羽流木はない | ハル キ ワ ナイ | ワルギ ハナイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A22862500000 | Conflict worth a human look. Sixty publisher records say ワルギハナイ; fourteen NDL book records say ワルギ, ワナイ, which cannot be right because the given name is written in kana as はない. |
| 臼井ともみ | ウスイ トモミ | ウスイ トモミ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029251097 | Guess was right. |
| 「真夜中ぱんチ」製作委員会 | 「マヨナカ パン チ」 セイサク イインカイ | マヨナカパンチセイサクイインカイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A21870300000 | A production committee, not a person. |
| 寄北光 | キキタ ヒカリ | NOT FOUND | | | NDL creator and title アオハルに憑き物 both empty. A pixiv Comic one-shot with no book and no printed reading. |
| いとう階 | イトウ カイ | NOT FOUND | | | NDL creator returns only two 百合SFガイド index entries with no transcription. Title サバーキ empty; a COMIC OGYAAA!! web serial with no book. The artist's X handle @golem_inc gives nothing. |
| 大倉ナタ | オオクラ ナタ | オオクラ ナタ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033022884 | Guess was right. ニーディガールオーバードーズ anthology, 秋田書店. |
| 藤居にこ | フジイ ニコ | フジイ ニコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033472451 | Guess was right. 夜のクラゲは泳げない, the example work. |
| 米島游 | コメシマ ユウ | NOT FOUND | | | NDL creator and title 佐々木さんが消えた日の歌 both empty. |
| 駿馬京 | シュンバ キョウ | シュンメ ケイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032542328 | きみと観たいレースがある, the example work. Found by title; the creator index files this writer with a birth-year suffix. |
| 伊実 | コレザネ | NOT FOUND | | | Not a Japanese name. NDL's 入味 record lists ZCloud, 伊実 and 角川青羽 (上海) 文化創意有限公司 and gives a transcription for none of them, the same way it handles other Chinese webcomic credits. Drop the stored reading rather than replace it. |
| 矢立肇 | ヤタテ ハジメ | ヤダテ ハジメ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I000002956104 | Conflict worth a human look. All 27 NDL records say ヤダテ; general usage and the ニコニコ大百科 headword say ヤタテ, from 芭蕉's 矢立の初め. Sunrise publishes no furigana. Consider leaving this one blank until a licensor source settles it. |
| 倉瀬しの | クラセ シノ | クラセ シノ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I034569979 | Guess was right. |
| 月並甲介 | ツキナミ コウ スケ | ツキナミ コウスケ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031186031 | The example work. Kana were right, the boundary was in the wrong place. |
| 尾花沢軒栄 | オバナザワケン サカエ | オバナザワ ケンエイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I026436627 | アサルトリリィ : 一柳隊、出撃します!, and the example work carries the same reading. |
| 電撃G'sマガジン | デンゲキ G ' s マガジン | デンゲキジーズマガジン | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A24599800000 | A magazine, not a person. The reading comes from NDL's 電撃Ｇ’ｓマガジン編集部 heading, デンゲキジーズマガジンヘンシュウブ, with 編集部 removed. |
| 筒井テツ | ツツイ テツ | ツツイ テツ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031381125 | Guess was right. 推しが隣で授業に集中できない!, the example work. |
| 蛙田あめこ | カエダ ア メコ | カエルダ アメコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029506989 | The example work, オーバーラップ. |
| 三弥カズトモ | ミツヤ カズトモ | ミヤ カズトモ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029478689 | その者。のちに…, アース・スターエンターテイメント; 剣と魔法の税金対策 e-books agree with ミヤカズトモ. |
