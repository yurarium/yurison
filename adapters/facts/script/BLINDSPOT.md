# What `facts/script` cannot see

## It answers about characters, never about language

`has_script` is true of a Japanese word and of a single kanji in an English sentence. Whether the
string IS Japanese, in the sense a reader means, is not a character-class question and nothing here
attempts it.

## The letter tests and the safety net disagree on purpose

`has_kana` spans assigned letters and refuses `・`, because a separator is not a letter and treating
it as one made `flower・flower` come back as kana. `has_script` spans the hiragana and katakana
blocks entire, unassigned slots included, because it is what asks whether Japanese has reached an
English page and a miss there is visible to a reader.

So `has_script("flower・flower")` is true and `has_kana("flower・flower")` is false, and both are
right for their question. A caller that picks the wrong one gets a plausible wrong answer.

## Twenty-four narrower patterns remain

The census found thirty. Five now ask this module. The rest are specific: a katakana run of four or
more, a furigana bracket, a katakana tail, a kana-only line with one shop's punctuation allowed.
Each is a rule about one source's writing and folding them together would lose what makes them
useful, which is the same argument that kept the five matching keys apart.

## The compatibility range is written as an escape, and that was a bug once

`豈-﫿` and not the literal `豈`, because the literal is U+8C48 and a range written from it
spans Hangul and Yi. `test_interface` caught that within a minute of it being introduced, by asking
whether 싱 and ꀀ are Japanese.
