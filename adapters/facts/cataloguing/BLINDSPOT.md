# What `facts/cataloguing` cannot see

It reads one string and answers what a cataloguer put around a name. Everything below is a way that
answer is wrong while this module is working exactly as written.

## A publisher's own sign looks like an ISBD one

一迅社 prints ルミナス＝ブルー: one name with a full-width equals sign inside it. A spaced ASCII
` = ` is the ISBD shape for a parallel title, and the pattern here is deliberately loose enough to
catch every spelling of the mark, so a house that prints one is indistinguishable from a cataloguer
who transcribed one. `RULED` is the answer and it is a list somebody wrote: a name is in it because
the publisher's own catalogue page was read. Nothing here can grow that list, and a house whose sign
nobody has looked up is read as cataloguing.

## The source decides the shape and this does not know which source

MADB transcribes to a cataloguing standard. A shop writes a title the way its own template does. The
same punctuation means different things in the two, and this is handed a string with no idea where
it came from. `adapters/madb/extract.py` assembles what it reads and is where that context lives.

## A subtitle and a reissue marker are both after a colon

` : 完全版` is an edition statement and ` : 上巻の物語` is the book's own subtitle. `EDITIONS` is a
closed set of six markers and the test is membership, so a house that invents a seventh has its
edition read as a subtitle, which keeps the words and files the reissue under a name of its own.
That direction is the safe one: a wrong split invents a work, a wrong join erases one.

## It says nothing about which work an edition belongs to

Taking `X : 完全版` apart says the volume is a reissue. It does not say what it reissues. That join
is `data/work-aliases.yaml` and the curated alias, and where the base edition is not in the corpus
there is nothing to join to.
