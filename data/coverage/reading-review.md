# Reading review: mechanical readings of kanji titles

Scope: every entry in `data/names/titles.yaml` whose `reading_basis` is `analyser` or
`back-converted` **and** whose title contains kanji. That is **816 entries** (762 analyser, 54
back-converted) out of 1085 names in the file.

Proposing **61 corrections** (34 high confidence, 17 high confidence but word-boundary only,
10 medium confidence), grouped by confidence. Readings below are written segmented with
spaces, in the same style as the file, so the romaniser places word boundaries correctly.

Nothing in `titles.yaml` or `curated.yaml` has been edited. This is a proposal only.

---

## High confidence

The current reading is wrong and the correct reading is not in doubt.

| title | current reading | proposed reading | reason |
|---|---|---|---|
| 転生王女と天才令嬢の魔法革命 | `テンショウ オウジョ ト テンサイ レイジョウ ノ マホウ カクメイ` | `テンセイ オウジョ ト テンサイ レイジョウ ノ マホウ カクメイ` | 転生 is てんせい; テンショウ is not a reading the compound takes. |
| 転生王女と天才令嬢の魔法革命 【タテスク】 | `テンショウ オウジョ ト テンサイ レイジョウ ノ マホウ カクメイ   【タテスク】` | `テンセイ オウジョ ト テンサイ レイジョウ ノ マホウ カクメイ   【タテスク】` | Same title, same 転生 fault. |
| 病弱少女、転生して健康な肉体（最強）を手に入れる　～友達が欲しくて魔境から旅立ったのですが、どうやら私の魔法は少しおかしいようです！？～ | `ビョウジャク ショウジョ、 テンショウ シテ …` | `ビョウジャク ショウジョ、 テンセイ シテ …` | 転生して is てんせいして. |
| 病弱少女、転生して健康な肉体(最強)を手に入れる ～友達が欲しくて魔境から旅立ったのですが、どうやら... | `ビョウジャク ショウジョ、 テンショウ シテ …` | `ビョウジャク ショウジョ、 テンセイ シテ …` | Truncated variant of the same title, same fault. |
| 死神少女は陰から推しを眺めたい　─悪役にTS転生したけど、こっそり原作キャラを観察しに行きます！─ | `… ─ アクヤク ニ TS テンショウ シタケド、 …` | `… ─ アクヤク ニ TS テンセイ シタケド、 …` | TS転生 is TSてんせい. |
| 悪役令嬢の中の人〜断罪された転生者のため嘘つきヒロインに復讐いたします〜 | `… ダンザイ サレタ テンショウシャ ノ タメ …` | `… ダンザイ サレタ テンセイシャ ノ タメ …` | 転生者 is てんせいしゃ. |
| 遠山えま百合集　センセイとの時間。 | `エンザン エ マ ヒャク ゴウシュウ 　 センセイ ト ノ ジカン。` | `トオヤマ エマ ユリシュウ 　 センセイ ト ノ ジカン。` | The author is Tōyama Ema, and 百合集 is ゆりしゅう, not 百 + 合集. |
| 結城友奈は勇者である 勇者部びより Party♪ | `ユウキ トモナ ワ ユウシャデ アル   ユウシャ ブ ビヨリ   Party ♪` | `ユウキ ユウナ ワ ユウシャ デ アル   ユウシャブ ビヨリ   Party ♪` | The character is Yūki Yūna; 勇者部 is ゆうしゃぶ; デ was glued to ユウシャ. |
| 大室家 | `オウムロ ケ` | `オオムロ ケ` | 大室 is おおむろ; オウムロ is a back-conversion of "ō" to the wrong kana. |
| ラブライブ!flowers*ー蓮ノ空女学院スクールアイドルクラブー | `ラブライブ ! flowers *ー レン ノ ソラ オンナ ガクイン スクールアイドルクラブー` | `ラブライブ ! flowers *ー ハス ノ ソラ ジョガクイン スクールアイドルクラブー` | 蓮ノ空女学院 is はすのそらじょがくいん; 女学院 is じょがくいん in every school name. |
| 紅殻のパンドラ | `ベニガラ ノ パンドラ` | `コウカク ノ パンドラ` | The title is こうかくのパンドラ, punning on 攻殻機動隊. |
| 紅魔館の女たち | `クレナイ マカン ノ オンナタチ` | `コウマカン ノ オンナタチ` | 紅魔館 is こうまかん; 紅 takes こう in the compound, not くれない. |
| 研究棟の真夜中ごはん | `ケンキュウ ムネ ノ マヨナカ ゴハン` | `ケンキュウトウ ノ マヨナカ ゴハン` | 棟 is とう in 研究棟; むね is the standalone kun reading. |
| 残光再撮 | `ザンコウ サイ ツマミ` | `ザンコウ サイサツ` | 再撮 is さいさつ; つまみ is 撮 in isolation, never in a Sino-Japanese compound. |
| 岐阜の善き魔女 | `ギフ ノ ゼンキ マジョ` | `ギフ ノ ヨキ マジョ` | 善き is the classical attributive よき; ゼンキ reads it as a noun compound. |
| 全部君のせいだ | `ゼンブクン ノ セイダ` | `ゼンブ キミ ノ セイダ` | 全部 and 君 are separate words; the analyser merged them and read 君 as くん. |
| 新刊100億冊ください | `シンカン イチレイレイオクサツ クダサイ` | `シンカン ヒャクオクサツ クダサイ` | 100億 is ひゃくおく, not the digits read one-zero-zero. |
| #うちらが最強 ～陰キャ除霊師とギャルJK～ | `# ウチラ ガ サイキョウ   ～ カゲ キャ ジョレイシ ト ギャル JK ～` | `# ウチラ ガ サイキョウ   ～ インキャ ジョレイシ ト ギャル JK ～` | 陰キャ is いんキャ, an established coinage from 陰気なキャラ. |
| ヒーローさんと元女幹部さん | `ヒーローサン ト ガンニョ カンブサン` | `ヒーローサン ト モト オンナ カンブサン` | The prefix 元 meaning "former" is もと; ガンニョ reads 元女 as a compound that does not exist. |
| お姉さまの言うとおり？ | `オ アネサマ ノ イウ トオリ？` | `オネエサマ ノ イウ トオリ？` | お姉さま is おねえさま, as the neighbouring お姉さん / お姉さま entries already have it. |
| 猫魔法が世界に革命を起こすそうですよ? | `ネコマ ホウ ガ セカイ ニ カクメイ ヲ オコス ソウデス ヨ ?` | `ネコ マホウ ガ セカイ ニ カクメイ ヲ オコス ソウデス ヨ ?` | The word boundary falls between 猫 and 魔法; 魔法 is まほう. |
| 殺し屋メイドは茨姫の夢を見る | `コロシヤ メイド ワ ウバラ ヒメ ノ ユメ ヲ ミル` | `コロシヤ メイド ワ イバラヒメ ノ ユメ ヲ ミル` | 茨姫 (Briar Rose) is いばらひめ; うばら is archaic and unused here. |
| 狼の皮をかぶった羊姫 | `オウカミ ノ カワ オ カブッタ ヒツジヒメ` | `オオカミ ノ カワ オ カブッタ ヒツジヒメ` | 狼 is おおかみ; オウカミ is a back-conversion of "ō" to the wrong kana. |
| 腹割るウチらの秘密ごと! | `フク ワル ウチラ ノ ヒミツゴト !` | `ハラ ワル ウチラ ノ ヒミツゴト !` | 腹を割る is はらをわる; ふく is 腹 only in Sino-Japanese compounds. |
| 腹割るウチらの秘密ごと！ | `フク ワル ウチラ ノ ヒミツゴト！` | `ハラ ワル ウチラ ノ ヒミツゴト！` | Full-width variant of the same title. |
| 四王天礼子の願望 | `シオウテン レイシ ノ ガンボウ` | `シオウテン レイコ ノ ガンボウ` | The character is Shiōten Reiko; 〜子 in a female given name is こ. |
| 黄道寮の星座な日々 | `オウドウ リョウ ノ セイザナ ヒビ` | `コウドウリョウ ノ セイザナ ヒビ` | The publisher's own page slug is `koudouryo`; 黄道 in the zodiac sense is こうどう. |
| レズっ娘クラブ ONE TiME ONLY | `レズッ ムスメ クラブ   ONE   TiME   ONLY` | `レズッコ クラブ   ONE   TiME   ONLY` | 〜っ娘 is 〜っこ; the group it is named after writes itself レズっ娘 = れずっこ. |
| 濡鴉の魔女 | `ジュカラス ノ マジョ` | `ヌレガラス ノ マジョ` | 濡鴉 is ぬれがらす; ジュカラス mixes an on reading with a kun reading. |
| 異種族女子に〇〇する話 | `イ シュゾク ジョシ ニ レイキゴウ スル ハナシ` | `イシュゾク ジョシ ニ 〇〇 スル ハナシ` | 〇 was expanded to its Unicode name ("zero symbol"); it is a censoring mark with no reading. The sibling entry using ○○ leaves it unread. |
| 限界OLと女子大生が〇〇する話 | `ゲンカイ OL ト ジョシダイセイ ガ レイキゴウ スル ハナシ` | `ゲンカイ OL ト ジョシダイセイ ガ 〇〇 スル ハナシ` | Same 〇 fault. |
| お姉さまと巨人 ～お嬢さまが異世界転生～ | `オネエ サマ ト キョジン` | `オネエサマ ト キョジン ～ オジョウサマ ガ イセカイ テンセイ ～` | The stored reading covers only the first half of the title; the subtitle is missing entirely. |
| 彩香ちゃんは弘子先輩を落としたい | `アヤカ チャン ワ ヒロコ センパイ ニ コイシテル` | `アヤカチャン ワ ヒロコ センパイ ヲ オトシタイ` | The stored reading is the reading of the sibling title 〜に恋してる, not of this one. |
| スケバンと転校生 | `スケバン ト テンコウセイ ガ クダラナイ アソビ オ スル ダケ ノ ハナシ` | `スケバン ト テンコウセイ` | The reading carries a longer title than the one stored; the tail has no counterpart in the name. |

## High confidence, word-boundary only

The kana are right; the spaces are in the wrong places, so the romaniser breaks or joins words
incorrectly.

| title | current reading | proposed reading | reason |
|---|---|---|---|
| しあわせ鳥見んぐ | `シアワセ トリミ ン グ` | `シアワセ トリミング` | 鳥見んぐ is a pun on とりみんぐ; ん and ぐ are not words. |
| 堕天使そぷらのちゃんの復讐 | `ダテンシ ソ プラ ノチャン ノ フクシュウ` | `ダテンシ ソプラノチャン ノ フクシュウ` | そぷらのちゃん is one name, Soprano-chan. |
| 香原さんのふぇちのーと | `カハラサン ノ フェ チ ノー ト` | `カハラサン ノ フェチノート` | ふぇちのーと is one word, fechi-nōto. |
| ほうかご再テンセイ！ | `ホウ カ ゴ サイ テンセイ！` | `ホウカゴ サイ テンセイ！` | ほうかご is 放課後 written in kana, one word. |
| やしろの魔王 | `ヤ シロ ノ マオウ` | `ヤシロ ノ マオウ` | やしろ (社) is one word. |
| 魔女とくゅらす | `マジョトク ュラス` | `マジョ ト クュラス` | The boundary falls after 魔女; the current split produces a nonsense first token. |
| 酒と鬼は二合まで | `サケ ト オニワ ニ ゴウ マデ` | `サケ ト オニ ワ ニ ゴウ マデ` | 鬼 and the particle は were glued into オニワ. |
| 幕末女子高生 鬼と夜明け | `バクマツ ジョシコウセイ   オニト ヨアケ` | `バクマツ ジョシコウセイ   オニ ト ヨアケ` | 鬼 and the particle と were glued into オニト. |
| 神の右手 | `カミノ ミギテ` | `カミ ノ ミギテ` | 神 and the particle の were glued into カミノ. |
| 昨日シたのに覚えてないの？ 百合えっち短編集 | `キノウシタ ノ ニ オボエテナイ ノ？ …` | `キノウ シタ ノニ オボエテナイ ノ？ …` | 昨日 and シた were glued; のに is one particle. |
| こもぐちゃんに食べられたい！ | `コモ グチャン ニ タベラレタイ！` | `コモグチャン ニ タベラレタイ！` | こもぐちゃん is one name. |
| 天瀬ましろはイきたくない！ | `アマガセ マ シロ ワ イキタク ナイ！` | `アマガセ マシロ ワ イキタク ナイ！` | ましろ is one given name. |
| 新米勇者のおしながき～乃木若葉は勇者である すぴんあうと４コマ～ | `… ユウシャデ アル  ス ピン アウト ヨン コマ ～` | `… ユウシャ デ アル  スピンアウト ヨンコマ ～` | すぴんあうと is one word; ４コマ is よんこま. |
| 抱き寝ーター | `ダキ ネー ター` | `ダキネーター` | The title is a single coined word, dakinētā. |
| 重しれー女 | `オモシ レー オンナ` | `オモシレー オンナ` | 重しれー is おもしれー, a colloquial 面白い, one word. |
| 御羊ちゃんは触りたい | `オ ヒツジチャン ワ サワリタイ` | `オヒツジチャン ワ サワリタイ` | おひつじ is one word (as in おひつじ座); the honorific お does not stand alone. |
| 七限目は忍者修行です！ | `ナナゲン メ ワ ニンジャ シュギョウデス！` | `ナナゲンメ ワ ニンジャ シュギョウデス！` | 限目 is げんめ; the split leaves 目 as its own word. |

## Medium confidence

The current reading looks wrong for the reasons given, but the correct reading rests on a
judgement about the work rather than on a fixed dictionary form. Worth a human check before
applying.

| title | current reading | proposed reading | reason |
|---|---|---|---|
| ダメ犬彼女 | `ダメケン カノジョ` | `ダメイヌ カノジョ` | ダメ犬 is だめいぬ; the on reading けん does not attach to a katakana stem. |
| イトが搦ム | `イト ガ カラミム` | `イト ガ カラム` | 搦ム is からむ in historical kana; カラミム reads the stem twice. |
| 上伊那ぼたん、酔へる姿は百合の花 | `カミイナ ボタン、 ヨイ ヘル スガタ ワ ユリ ノ ハナ` | `カミイナ ボタン、 ヨエル スガタ ワ ユリ ノ ハナ` | 酔へる is historical kana for 酔える, よえる; the analyser read へ as a separate mora. |
| 潮滅に沈む翡翠、北のまちの黒曜 | `シオ メツ ニ シズム カワセミ、 キタ ノ マチ ノ コクヨウ` | `シオ メツ ニ シズム ヒスイ、 キタ ノ マチ ノ コクヨウ` | Paired with 黒曜 (obsidian), 翡翠 is the gemstone ひすい, not the bird かわせみ. |
| 三年坂 | `サン ネン サカ` | `サンネンザカ` | 三年坂 is さんねんざか, a single place name with rendaku. |
| ７日間限定彼女 | `ナナ カカン ゲンテイ カノジョ` | `ナノカカン ゲンテイ カノジョ` | 七日間 is なのかかん; ナナカカン is not a form the counter takes. |
| かいじゅう色の島 | `カイジュウショク ノ シマ` | `カイジュウ イロ ノ シマ` | 色 attached to a kana stem is いろ; しょく belongs to Sino-Japanese compounds. |
| ほぐして、癒衣さん。 | `ホグシテ、 イエ コロモサン。` | `ホグシテ、 ユイサン。` | 癒衣 is a given name; ゆい is the ordinary reading, and イエコロモ is two isolated kun readings. |
| 縁切鋏 | `エンキリ ハサミ` | `エンキリバサミ` | 鋏 rendakus to ばさみ as the second element of a compound. |
| 金小路家の恋愛指南 | `コンゴウジカ ノ レンアイ シナン` | `カネコウジ ケ ノ レンアイ シナン` | 〜家 after a surname is け, not か; 小路 in a surname is こうじ. The surname's first element is the less certain part. |

---

## Considered and not proposed

Flagged by the sweep but left alone, because a reading I merely find unusual is not a correction.

- **白月光プロジェクト〜あの時の彼女を取り戻す〜【タテスク】** — `シロ ゲッコウ プロジェクト …`.
  シロゲッコウ mixes a kun and an on reading and is probably wrong, but the work's own blurb
  furiganas 白月光 as ムーンライト, and I could not establish what the title itself takes.
- **英雄少女と呪われの銀姫** — `… ノロワレ ノ ギンキ`. 銀姫 could be ぎんき or ぎんひめ; no basis to choose.
- **南山除妖録** — `ナンザン ジョ アヤカシロク`. 除妖録 is a coinage; じょようろく is likelier than アヤカシロク but unverified.
- **湾田さんと蛇ノ目さん** — `ワンデンサン …`. 田 as でん is odd in a surname, but the surname is invented and unknowable.
- **姫と女勇者が結ばれるための12の聖行為** — `ヒメ ト ジョ ユウシャ …`. Both じょゆうしゃ and おんなゆうしゃ occur in this genre.
- **嫌われ魔女令嬢と男装皇子の婚約** — `… ダンソウ ミコ …`. 皇子 takes both おうじ and みこ.
- **琥珀の貴女** — `コハク ノ キジョ`. 貴女 is あなた in most yuri titles but きじょ is a real word and fits an amber-themed title.

## Separate, systematic: を back-converted to ウォ

Five `back-converted` entries write the particle を as ウォ. を is read お, so ウォ is not a reading
of it, though the romaniser's `wo` output happens to be a conventional particle spelling. Listing
for completeness rather than proposing individually:

- あなたが私を変えたから — `アナタ ガ ワタシ ウォ カエタカラ`
- あなたの未来を許さない — `アナタ ノ ミライ ウォ ユルサナイ`
- この恋を星には願わない — `コノ コイ ウォ ホシ ニ ワ ネガワナイ`
- オタクには人生を積むことしかできない — `オタク ニ ワ ジンセイ ウォ ツム コト シカ デキナイ`
- カナリアは綺羅星の夢をみる — `カナリア ワ キラボシ ノ ユメ ウォ ミル`

The rest of the file writes the particle as ヲ (analyser entries) or オ (other back-converted
entries), so these five are also inconsistent with their own neighbours.
