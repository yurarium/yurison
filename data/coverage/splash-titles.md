# Latin titles printed on series art

A sampling pass over the 952 works whose stored English is ours — a romanisation or a translation
we wrote — looking for works that print their own Latin title on their artwork, the way ゆりゾン
prints `yurison` under the kana.

**104 works examined by eye. 49 carry a Latin form of their own title; three more already had a
Latin title and the art confirms it.**

Every reading below was made by looking at the image. OCR appears nowhere in the results; it was
used only to order the queue, and it turned out to be barely worth having.

## Method

1. Every one of the 952 candidates had its page fetched once, 1.5 s between requests to a host,
   identified as `yurarium/0.1`. 947 resolved to a page and 895 to a downloadable artwork file.
   On GigaViewer sites the artwork is the `series-thumbnail`, which on the Ichijinsha and Kodansha
   imprints is the work's own splash page; elsewhere it is `og:image`. カドコミ and pixivコミック
   needed their own handling.
2. Images were then opened and read, 104 of them so far. Latin set in small type was re-cropped
   from the original file at up to 4x and read again; six of the findings needed that.
3. Corroboration was sought in the page source. GigaViewer episode pages carry a `content_id`, and
   on a few imprints that field is a Latin slug of the title.

**Calibration.** The pipeline was run first against ゆりゾン, which is not in the candidate list
because it is already resolved. Its series thumbnail
(`cdn-img.comic-ogyaaa.com/public/series-thumbnail/2550912965728492745-…`) shows `yurison` in lower
case beneath the kana logo, and the episode page carries `content_id: YURISON_001`. Both
reproduced, so the method finds what it is meant to find.

**What OCR was worth.** Tesseract read the ゆりゾン logo as `yu cison`, so it was never allowed to
rule a work out. Its ranking was checked against a random control sample drawn from everything it
scored low. Of 69 works from the top of its ranking, 38 were findings; of 24 works drawn at random
from the tail, 10 were findings. A lift from 42% to 55% is not worth trusting a filter over, and
the practical conclusion is the useful one: **the base rate is high enough that random sampling
works nearly as well as any ranking**. Someone continuing this can just walk the list.

## Cases

- **(a)** the art carries a Latin form of the title — the only kind of finding
- **(b)** the art carries Latin that is not the title: an author's name, an imprint, a tagline
- **(c)** no Latin on the art at all

The discriminator used throughout is placement. Latin set inside the title lockup — above, below or
threaded through the Japanese logo, in the same design — is the title. Latin sitting apart from it
is not, however English it looks. `Presented by Hoshino Kanata.` at the foot of a 一迅プラス splash
page is case (b), and something of that shape appears on most of them.

## Findings — case (a)

Where the corroboration column says *art only*, the evidence is the image itself and the image URL
is given so the reading can be checked. Nothing else on the platform repeats the string.

| work | our current English | Latin form on the art | corroboration | confidence |
| --- | --- | --- | --- | --- |
| ゆりゾン *(calibration; already resolved)* | Yurizon | `yurison` | `content_id: YURISON_001`, https://comic-ogyaaa.com/episode/2550912965728497650 | high |
| オカワリいただけただろうか? | Would You Like Seconds? | `OKAWARI ITADAKETA DAROUKA?` | `content_id: okawari_010_5` in the source of https://comic-action.com/episode/12207421983881261105 | high |
| 梓月は天に咲う | Azuki Smiles at the Sky | `ADUKI HA SORA NI WARAU` | printed twice on the one page, in the title cartouche and again along the foot. Fixes 梓月 as あづき | high |
| きみと世界の終りを訪ねて | Visiting the End of the World with You | `Keep the END` | set as the main title with the Japanese below it; the foot repeats `Keep the END just a little longer / presented by KORUSE / published by ICHIJINSHA` | high |
| ひかりのすむところ | Where the Light Lives | `Where the light lives.` | art only: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923184092-2e15647e1ef13dfc77c0aec0ce76c460 | high |
| 百合バリズム部 | The Yuri Barizumu Club | `YURIBALISMBU` | art only: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923184621-8b5f7115d75885badfd4af6f76725ede | high |
| エクストリームスーパーダーリン | Extreme Super Darling | `Extreme Super Darling` | art only: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965919360703-7f0e5f00bed1d2752443413dd2446999 | high |
| 今宵、悪役令嬢の手をとれたら | Tonight, If I Could Take the Villainess's Hand | `Dancing with you on the snowy night` | art only, read from a 4x crop: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965913086126-fe0591844c36ae7129356fd91bf07285 | medium-high |
| 残存の竜 | The Surviving Dragon | `Remaining Dragon` | art only: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923184515-3e4fde0cfe66cbad2ad1a6837d3bd92e | high |
| かたわれの女神 | The Goddess Who Was My Other Half | `Kataware no Megami` | art only: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923184265-7c3c58859fdbedbb44fe8a3edd272bac | high |
| ドロップアウト・サキュバス！ | Dropout Succubus! | `Drop out♡Succubus!` | art only: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923184524-ff9c441c82bcb2a2c5647ab257deec06 | high |
| 悪役令嬢とギャルメイド | The Villainess and Her Gal Maid | `Villainess & GALmaid` | art only, read from a 4x crop; the mixed case of `GALmaid` is deliberate and legible | medium-high |
| いととうとし | A Thread, So Precious | `Ito-Toutoshi` | art only: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912966047837745-d6b907b3d102a433a89a0b9fcca820c1 | high |
| マジックアワー | Magic Hour | `MAGIC HOUR` | art only: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923183855-984b1275596e501338247c536f0c2dc9 | high |
| 私だって青春したいですよ、本当は。 | I Want a Youth Too, Honestly. | `The truth is, I want to enjoy my youth too.` | volume 1 cover: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912966077785019-b848daf93629b05d38b588831e70982c | high |
| 私の知ってるお姉さん | The Onee-san I Know | `A LADY I KNOW` | art only, 4x crop; the same cartouche carries `PRESENTED BY AKARI OTOKAWA`, which is case (b) | medium-high |
| ジュリア・イン・ザ・ボックス！ | Julia in the Box! | `Julia in the box!` | art only: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965919360550-2c5cce614f5bc6926d1b98909c192056 | high |
| 僕らのアイは気持ち悪い | Our Love Is Disgusting | `OUR "LOVE" IS DISGUSTING.` | art only, 4x crop: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923184075-37f955d0cf6786d07b4296ad27b4b59b | high |
| 好きな人が指輪をつけてきた | The Girl I Like Showed Up Wearing a Ring | `Someone you love is wearing a ring` | art only, 4x crop. Printed on a character's shirt rather than in the lockup, so read it as a gloss the artist put on the page, not necessarily an official second title: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965919360579-ba20d939e4c09c70ff25b5e46dcc7680 | medium |
| 御羊ちゃんは触りたい | Little Miss Sheep Wants to Touch | `OHITSUJI CHAN HA SAWARITAI` | art only; fixes 御羊 as おひつじ: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923184172-3a7d7feb9162bd41d4316dad978e257e | high |
| 私に天使が舞い降りた！ | Wataten!: An Angel Flew Down to Me | `watashi ni tenshi ga maiorita!` | letterspaced along the foot of the volume 13 cover: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923183565-7d6b59b6ac4e8f456302472268607fc6 | high |
| 超深宇宙より愛をこめて | From the Deepest Space, with Love | `Big love from ultra deep space` | volume 1 cover: https://cdn-img.ichicomi.com/public/series-thumbnail/2550912965923183753-e70085c3b50d66d5085017fd69209c7a | high |
| フードコートで、また明日。 | See You Tomorrow, at the Food Court. | `SEE YOU TOMORROW, AT THE FOOD COURT.` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/005741/25002c5d-1d1b-4af8-9de2-254559378bcc.jpg | high |
| あたし達って付き合ってるよね!? | We're Going Out, Aren't We?! | `WE ARE DATING, RIGHT!?` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/011928/99fa1075-a222-48c0-9827-a28d61c5a311.jpg | high |
| 新米姉妹のふたりごはん | The Rookie Sisters' Meals for Two | `Let's have a meal together!` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/002743/e6387263-772e-4f4f-ab5e-2be512f84390.jpg | high |
| あきらかに年齢を詐称している女子高生VTuber | The Schoolgirl VTuber Who Is Plainly Lying About Her Age | `High school girl VTuber who clearly lies about her age` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/009434/54410ec9-085b-4cc7-812a-64a138fa0137.jpg | high |
| 七限目は忍者修行です！ | Seventh Period Is Ninja Training! | `THE SEVENTH PERIOD IS NINJA TRAINING!` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/007122/b644bbca-683c-46a9-88a8-16e68a6755a8.jpg | high |
| お菊さんはいちゃ憑きたい | Okiku Wants to Get Cozy (and Haunt You) | `okiku-san wa ichatsukitai` | art only; fixes 憑き as つき: https://cdn.comic-walker.com/integration/cdpf/resources/002468/75ee8a1e-af04-4647-b058-546d77bc4fc6.jpg | high |
| ムショカノジョ | Prison Girlfriend | `MUSYOKANOJO` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/019393/fc739d1e-8d59-427c-ace3-417bddd1b2c7.jpg | high |
| 葬られたきみへ | To You Who Were Buried | `To You Who Were Buried.` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/005851/0b964113-351a-43d6-b011-572f91a292d2.jpg | high |
| 魔王と百合 | Maou to Yuri | `MAOU TO YURI` | art only; the line under it, `the world will perish, if she doesn't choose her companion.`, is a tagline and is case (b): https://cdn.comic-walker.com/integration/cdpf/resources/004382/e4076b72-3145-40cc-88ae-dcd21368ca80.jpg | high |
| 彼女のカノジョと不純な初恋 | Her Girlfriend and an Impure First Love | `MY GUILTY FIRST LOVE WITH ANOTHER GIRL'S GIRLFRIEND` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/009359/f52ddbe4-8845-4520-954f-504bc1985354.jpg | high |
| 両片想いな双子姉妹 | The Twin Sisters with Matching One-Sided Crushes | `ryokataomoi na futago shimai.` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/000549/855241b1-dbe7-4298-a692-9326915dd899.jpg | high |
| イジめてイジられて | Bullying and Being Bullied | `ijimete ijirarete` | art only, 4x crop; set in tiny type following a chain over the logo: https://cdn.comic-walker.com/integration/cdpf/resources/019052/5e3d0556-f365-462d-b141-c5eb650892e3.jpg | medium-high |
| ニニンがシノブ伝ぷらす | Ninin ga Shinobuden Plus | `2×2＝SHINOBUDEN+` | art only: https://cdn.comic-walker.com/integration/cdpf/resources/003297/1bd91869-65b9-4a18-ad9f-2ae9f55d17dc.jpg | high |
| かわいいのなにが悪いの？ | What's Wrong with Being Cute? | `kawaii no naniga waruino?` | art only, set vertically beside the logo: https://cdn.comic-walker.com/integration/cdpf/resources/007022/1e910b29-0c69-420f-b698-662cad520b06.jpg | high |
| うさぎはかく語りき | Thus Spoke the Rabbit | `ALSO SPRACH FOR RABBIT` | art only; `FOR RABBIT` stands where the は of the Japanese sits, inside the title plate: https://img.comic-fuz.com/c/1CL2d7/oh.webp | high |
| しあわせ鳥見んぐ | Happy Birding | `HAPPINESS BIRD WITHIN YOU.` | art only: https://img.comic-fuz.com/c/1CSlK_/oP.webp | high |
| ももいろモンタージュ | Peach-Colored Montage | `Momoiro Montage` | art only: https://img.comic-fuz.com/c/1CwTTh/nS.webp | high |
| 紡ぐ乙女と大正の月 | The Spinning Maiden and the Taishō Moon | `A DRIFT GIRL AND A NOBLE MOON` | art only: https://img.comic-fuz.com/c/1Bide3/la.webp | high |
| 夜と海 | Night and Sea | `Night and Sea` | art only: https://img.comic-fuz.com/c/1Ck6x5/nD.webp | high |
| トワ・エ・モア | Toi et Moi | `toi et moi` | volume 1 cover, all lower case, beneath `KCDX BETSUFURE`: https://cdn-img.comic-days.com/public/series-thumbnail/2550689798274437681-2a477429a34b3b77ce66f8a7a4afb76a | medium-high |
| らぶ あんど ぴーす | Love and Peace | `LOVE & PEACE` | art only, under the logo: https://cdn-img.comic-days.com/public/episode-thumbnail/14079602755274553787-ed279bd3bacdee673f1794f7001b236e | high |
| 大好きな親友がVチューバーの自分にガチ恋してた話 | The Story of My Beloved Best Friend Being Seriously in Love with My VTuber Persona | `MY BEST FRIEND IS IN LOVE WITH MY VTUBER` | volume cover, set vertically: https://cdn-img.comic-action.com/public/series-thumbnail/4856001361584720983-b229503c79c6ee552ad451439ccca210 | high |
| 彩香ちゃんは弘子先輩に恋してる | Ayaka Is in Love with Hiroko-senpai | `AYAKA is in LOVE×LOVE×LOVE with HIROKO` | volume 3 cover: https://cdn-img.comic-action.com/public/series-thumbnail/13933686331667100482-ac182f9bec61f508287f1676904ef6cc | high |
| 魔女の孫と七人のメイド | The Witch's Granddaughter and the Seven Maids | `The Witch's Granddaughter and Seven Maids` — no *the* before *Seven* | volume cover: https://cdn-img.comic-action.com/public/series-thumbnail/11341664176597597354-cf337eaf2c77b3300b8435cf0987c57d | high |
| 百合オタに百合はご法度です!? | Yuri Is Forbidden for a Yuri Otaku!? | `yuriota ni yuri wa gohatto desu!?` | volume cover: https://cdn-img.comic-action.com/public/series-thumbnail/13933686331613280400-eedad91e5e6cd5d4b3a52bc28ba442e0 | high |
| あなたの未来を許さない | I Won't Forgive Your Future | `I will not forgive Your Future.` | art only: https://cdn-public.comici.jp/series/473271/2024120412334196151477270C3D5FA4CD35529AB8DB238E1.webp | high |
| ステラ・ステップ | Stella Step | `Stella` / `Step`, split above and below the katakana | art only: https://cdn-public.comici.jp/series/1646812/20250624122143882D17345FE433856874F936436F772ABB7.webp | high |
| この百合はフィクションです | This Yuri Is Fiction | `This GL is fiction` | art only; note **GL**, not *yuri*: https://manga-park.com/static/t/1e0t/i/1$wrOWwgw.jpg | high |

## Already Latin, and the art agrees

These are in the candidate list because our English differs from the Japanese title string, not
because the title needed romanising.

| work | our current English | Latin form on the art | corroboration | confidence |
| --- | --- | --- | --- | --- |
| Where I Belong(第96回新人コミック大賞・佳作) | Where I Belong | `【Where I Belong】` | https://cdn-public.bigcomics.jp/series/19/20250609104034202131DD38CBD0F1EF903ECF294B3330FAA.webp | high |
| Killer♡Twinkle～アンチはステージに上がれません♡～ | Killer♡Twinkle ~Anti-Fans Don't Get to Take the Stage♡~ | `Killer♡Twinkle`, with キラートウィンクル as furigana; the subtitle stays Japanese | https://cdn-public.comici.jp/series/1604039/20251211172553496D6870830884E9B1895DC7CFAD3B1B587.webp | high |
| 【今日の10ページ】BREAD NEW DAY | BREAD NEW DAY | `BREAD NEW DAY` | https://cdn-img.magcomi.com/public/series-thumbnail/2550912964518979142-2e120d183b13461f642ef8ff292cf867 | high |

## Case (b), recorded so we do not re-open them

Latin on the art that is **not** the title:

- **author names** — 4時半、コインランドリーにて (`Presented by Hoshino Kanata.`), マーメイドライン
  (`Renjuro Kindaichi`, plus a `yuri-hime comics` imprint mark), 私の小さなおひめさま
  (`by Hino Arashi`), 文系のきみ、理系のあなた (`Presented by`), あこがれを結んで (`kanato ichigo`),
  いっそ、恋だったらよかったのに (`Rui Obata presents`), よくばれ! 人間さん (`HIBI OISHI`),
  きみがわるい！ (`presented by TOGANE SAKURA`)
- **a magazine logo** — 殺し屋メイドは茨姫の夢を見る carries `Comic Ride ivy`, which is the magazine
- **decorative English** — ゆり×こちょ！ sets `coochie-coochie-coo!` and `stop tickling me!` around
  the logo. They gloss こちょ but they are not a title form
- **a tagline** — 溺れて、愛毒 carries `Be addicted to love toxic......` in the header and again
  vertically. It reads as ad copy, so it is excluded on the strict rule, though it is the closest
  call in the set and worth a second opinion

## Which platforms carried usable art

This is the part worth acting on. Ordered by how often the artwork can settle the question.

| platform | in list | art reached | what the art is | hit rate seen |
| --- | --- | --- | --- | --- |
| 一迅プラス | 109 | 109 | the work's own splash page or volume cover, title lockup and all | very high — Yuri Hime routinely sets a Latin line in the lockup; 20 of the 34 opened were findings |
| カドコミ | 206 | 206 | a wide key-art banner carrying the title logo | very high — 14 of 22 opened were findings, and the banner is usually large enough to read without cropping |
| COMIC FUZ | 36 | 36 | key art with a designed title plate | high — 5 of 5 opened were findings |
| webアクション | 16 | 16 | volume covers | high — 5 of 6 opened; also the one platform where `content_id` corroborated a reading |
| comici sites (竹コミ, チャンピオンクロス, キミコミ, コミックPASH! neo, Gコミ, ライコミ, …) | ~80 | all | a 2560×1344 key-art banner | mixed, but the files are large and legible; nothing here was unreadable |
| コミックDAYS | 94 | 94 | uneven: sometimes the title page or volume cover, often an interior panel | low to moderate — 2 of 6 opened were findings |
| ビッコミ | 25 | 25 | the title splash | usable; small sample |
| となりのヤングジャンプ | 81 | 81 | mostly a square award or teaser tile with the title in Japanese | low; mostly case (c) |
| サンデーうぇぶり | 64 | 64 | a promotional banner in Japanese, or an interior panel | low; mostly case (c) |
| 少年ジャンプ+ | 46 | 46 | a square cover tile | low |
| MAGCOMI | 21 | 21 | series thumbnail, often an interior panel for the 今日の10ページ one-shots | low |
| pixivコミック | 47 | 5 | an anthology or volume cover | unusable, see below |

**pixivコミック is the one platform that did not work.** The series page is client-rendered and
carries no image in its HTML. Its JSON API (`comic.pixiv.net/api/app/works/v5/{id}`) serves the
cover, but it returned 403 after a handful of calls, so 42 of the 47 have no artwork here. Even
where it worked the cover belongs to the anthology volume rather than to the individual work, which
is the wrong object: the first one checked, Mな王子の愛し方, is one of five stories inside
女子校の王子様は私しか眼中にないらしい 百合アンソロジーコミック①.

## Where corroboration came from, and where it did not

The `content_id` channel that settled ゆりゾン is real but thin. Of the 947 pages fetched, 93 carry
a Latin `content_id`, and most of those are lower-case internal slugs (`joshiman_018`,
`fuwamomi_0001`, `sayobara_001-1`) or event codes (`comitia153_7_0001`) rather than a title as
printed. Only COMIC OGYAAA!! uses the upper-case `TITLE_001` form that made `YURISON_001` so
legible. Across the works whose art was read, exactly one had its reading confirmed this way:
オカワリいただけただろうか? against `okawari_010_5`.

カドコミ's page JSON was checked directly and carries no Latin field at all — no `titleKana`,
no slug, only the `KC_nnnnnn_S` product code. So for カドコミ the art is the only evidence
available on the platform, and the image URL in the table is the citation.

## Could not read

Nothing was guessed. Where the type was too small to read from the plain image it was cropped from
the original file and read there, and the confidence column says so: the four marked medium-high
(`Dancing with you on the snowy night`, `Villainess & GALmaid`, `A LADY I KNOW`, `ijimete
ijirarete`) and the one marked medium (`Someone you love is wearing a ring`, which is legible but
whose placement on a garment makes its status as a title arguable) are the whole of the doubt in
this table.

## What is left

848 of the 952 have not been looked at, and 791 of those have artwork already downloaded. Given the
measured base rate — near half of everything opened is a finding — there is a lot left. The order
to work in is 一迅プラス, then カドコミ, then COMIC FUZ and webアクション; skip pixivコミック until
someone solves its API.
