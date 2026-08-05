# Author readings, tail

22 names checked. 20 readings found, 2 not found.

Of the 20 found, one differs from the machine guess in kana rather than spacing: 宇島葉 was stored
as ウノシマ ハ and reads ウノシマ ヨウ. Three more differ only in where the family/given boundary
falls (千野なこ チノナ コ for チノ ナコ, 富沢未知果 トミザワ ミチ カ for トミザワ ミチカ, 山口えいと
ヤマグチ エイ ト for ヤマグチ エイト). The remaining sixteen match the guess exactly, which is a
higher hit rate than earlier rounds and reflects what this tail is made of: most of these names
belong to artists with a KADOKAWA or 芳文社 tankōbon under the same characters, so the guesser had
an easy target.

Two names to look at twice even though the kana came out unchanged. 姫海月スグル reads キクラゲ
スグル, not a compositional reading of 姫海月, and NDL carries it that way on both the KADOKAWA book
and the 小学館 digital record. 高橋哲哉 is catalogued by NDL under the alternate pen name 高橋てつや
for the very book カドコミ credits to 高橋哲哉, so the reading タカハシ テツヤ is attested but the
name form is not; the artist debuted in 2006 and uses both spellings.

The two not found are both contributors to セフレ沼から抜け出せないっ！百合えっちアンソロジー
(一迅社, 2026.8). NDL holds the collected volume with no creator field at all and has not catalogued
the per-story 単話 records, which is what resolved the two メロウ・アンビバレンス contributors in
this same batch. 生肉 also deposits doujinshi through the circle 食べ放題, and those records carry a
title transcription but no creator transcription. The stored guess for 生肉, セイニク, is contradicted
by the artist's own X handle @namanoniku0005, so it should be dropped rather than kept; a handle is
not a catalogued reading and no source was found that gives one.

Method: `https://ndlsearch.ndl.go.jp/api/opensearch?creator=<name>`, falling back to `?title=<work>`
and `?any=<name>`, reading `dcndl:creatorTranscription` positionally against `dc:creator`. The
positional pairing carried 六野瀬えんじ, 千野なこ and 赤樫, all of whom appear on multi-contributor
一迅社 or KADOKAWA 単話 records rather than on a book of their own. Every match was checked against
the other titles on the record: 高橋哲哉, 荒木美咲, 広瀬まどか and 原百合子 all return large numbers
of NDL records under the exact characters that belong to a philosopher, a librarian, a nurse and
several medical researchers, and those were rejected by title. 赤樫 was confirmed through the カドコミ
author page, which lists たびみまん and 薬売りの聖女 under one author id, so the NDL reading on the
latter applies to the former. Requests went out as `yurarium/0.1` at roughly 1.6s apart.
ndlsearch.ndl.go.jp returned 503 on its HTML record pages throughout, so every NDL citation below
was read through the OpenSearch API and the URL is given for the human-readable record it names.

| name | machine guess | proposed reading | source kind | URL | note |
|---|---|---|---|---|---|
| ふじい葛西 | フジイ カサイ | フジイ カサイ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032352948 | 悪役令嬢が正ヒロインを口説き落とす話。, KADOKAWA, the database's own work. Around 30 aligned records across 道玄坂書房, キルタイムコミュニケーション and ぶんか社. |
| 六野瀬えんじ | ロクノセ エンジ | ロクノセ エンジ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I7580000000024020726L | 一迅社 単話 record for メロウ・アンビバレンス, the one story in the anthology. Sole creator on the record. |
| 千野なこ | チノナ コ | チノ ナコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I7580000000034020726O | 一迅社 単話 record for 知らないあなた. Guess split the name a syllable too late. |
| 卯花つかさ | ウノハナ ツカサ | ウノハナ ツカサ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032777113 | ごきげんよう、一局いかが?, 芳文社, the database's own work. Same creator index as アニマエール!. |
| 原百合子 | ハラ ユリコ | ハラ ユリコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029183983 | 繭、纏う, KADOKAWA, the database's own work. Also aligned on the 一迅社 単話 嘘の理由. NDL is crowded with 篠原/杉原/萩原百合子; the title isolates the artist. |
| 姫海月スグル | キクラゲ スグル | キクラゲ スグル | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I031184504 | ふらちな倫理ちゃん, KADOKAWA. 姫海月 reads キクラゲ, confirmed again on the 小学館 record for 乙女たちの推しゴト. |
| 宇島葉 | ウノシマ ハ | ウノシマ ヨウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032360477 | 猫のまにまに, KADOKAWA, the database's own work. Five aligned records with 世界八番目の不思議. The stored ハ is wrong. |
| 富沢未知果 | トミザワ ミチ カ | トミザワ ミチカ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I033025461 | 恋の絶望行進曲, KADOKAWA, the database's own work and the only NDL record under the name. 未知果 is one given name. |
| 山口えいと | ヤマグチ エイ ト | ヤマグチ エイト | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I030009622 | 疲れきった女が死ぬほど癒やされるために。, KADOKAWA, the database's own work. 18 aligned records including the 小学館 すきだから、だよ run. |
| 広瀬まどか | ヒロセ マドカ | ヒロセ マドカ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029873251 | 神ゲーってそういうことですか, KADOKAWA, the database's own work. Nursing-journal records under 廣瀬まどか rejected. |
| 新井すみこ | アライ スミコ | アライ スミコ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032751174 | 気になってる人が男じゃなかった, KADOKAWA, the database's own work. Four volumes plus the Polish edition, all aligned. |
| 旭晨薫 | アサヒ アキシゲ | アサヒ アキシゲ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032807851 | ジャック・ジャンク・ジャンキー, KADOKAWA あすかコミックスDX, the database's own work and the only NDL record under the name. |
| 東洋トタン | トウヨウ トタン | トウヨウ トタン | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032670810 | ラストサマー・バケーション, KADOKAWA, the database's own work. 22 aligned records with 闘う翼に乾杯を。 and the 分冊版 run. |
| 浜弓場 双 | ハマユミバ ソウ | ハマユミバ ソウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I027263602 | おちこぼれフルーツタルト, 芳文社, the database's own work. Around 100 aligned records. |
| 狐ヶ崎 | キツネガサキ | キツネガサキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I030589649 | ドM女子とがっかり女王様, KADOKAWA, the database's own work. One unit, no family/given boundary. |
| 甘党 | アマトウ | アマトウ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I026722088 | となりの吸血鬼さん, KADOKAWA, the database's own work. Replaces the stored value, which was back-converted from a mangaupdates romanisation. |
| 生肉 | セイニク | NOT FOUND | | | NDL creator returns only 食べ放題 doujin deposits with no creator transcription; the 一迅社 anthology record has no creator field and no 単話 records exist. BOOK☆WALKER author page 154051 and ichicomi carry no kana. Drop the stored セイニク: the artist's X handle is @namanoniku0005. |
| 白玉もち | シラタマモチ | シラタマモチ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A14252100000 | わたしはサキュバスとキスをした【分冊版】, KADOKAWA, the database's own work. Around 20 aligned 分冊版 records; the self-published 白玉もち deposits carry no transcription. |
| 荒木美咲 | アラキ ミサキ | アラキ ミサキ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I032466048 | クラスのアイドルは今日も推せない, KADOKAWA, the database's own work. The only other record under the name is a library-journal article and was rejected. |
| 赤樫 | アカガシ | アカガシ | national-library | https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A19728100000 | 薬売りの聖女【分冊版】, KADOKAWA, paired positionally against 榛名丼 and ＣＯＭＴＡ. Same カドコミ author id 018d6a5a-cdcf-7750-bc38-10d022c1204c as the database's たびみまん. Urology papers by 赤樫圭吾 rejected. |
| 高橋哲哉 | タカハシ テツヤ | タカハシ テツヤ | national-library | https://ndlsearch.ndl.go.jp/books/R100000002-I029873395 | はつ恋、ときめきうすいほん, KADOKAWA, the database's own work, catalogued under the artist's other pen name 高橋てつや. Also aligned on ドキドキしすたー葵ちゃん. The 100+ records under 高橋哲哉 belong to the philosopher (1956-) and were rejected. |
| 高良真生 | コウラ マサオ | NOT FOUND | | | NDL creator empty; `any=高良真生` returns only the 一迅社 anthology volume, which has no creator field, and the per-story 単話 records are not catalogued. No publisher, platform or artist page found that prints a reading. The stored コウラ マサオ is unsupported and 高良 is as often タカラ. |
