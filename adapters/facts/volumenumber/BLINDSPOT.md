# What `facts/volumenumber` cannot see

It reads one product title against one series title and reports what the shop wrote. Everything it
cannot see follows from that being all it is given.

## It cannot see whether the number is TRUE

The shop's own listing is the only witness. A product mislabelled `3巻` in the shop's catalogue is
reported as volume 3, confidently, and no amount of reading the title will find that out. What
catches it is another catalogue numbering the same book differently, which is VOLUMES-PLAN §3's
job and not this module's.

## It cannot see a number the shop states somewhere other than the title

コミックシーモア numbers a volume in its own field and BOOK☆WALKER does not, which is why this
exists at all. A shop that moves the number to a field, or a capture that stops recording the
product title, silently takes every number here to None. The count of unnumbered rows is the only
thing that would show it, so a jump in that count is worth reading as a capture change rather than
as a shop change.

## The 21% it declines are not all the same thing

Roughly a fifth of the rows state no number this can read, and they are at least three populations:
periodicals filed as series, shop-side umbrellas holding differently named books, and volumes whose
number is written in a form nobody has met yet. The module reports None for all three and cannot
tell them apart. Only the second is correct to leave unnumbered for ever.

## It cannot see that two products are the same volume

`is_sample` names the free samples, which is one way a listing repeats a volume. A special edition,
a reissue and a bundle also repeat one, under names this does not read. Deduplication belongs to
whatever holds the whole set, and this answers only about the title in front of it.

## The tolerant comparison can match too much

Accent, width, case and punctuation are removed before the series title is sought, so a series
called `A・B` matches a product called `AB`. That is what makes `MURCIÉLAGO` meet `MURCIELAGO`, and
it means a short series title made mostly of punctuation could be found inside a product title by
accident. No case of this exists in the corpus as measured, which is a statement about today's data
rather than about the rule.

## A volume's own name is read off its designation, and some designations are not one

`subtitle` and `position` split a designation into a name and a place in the run. They cannot see
a number glued to a name, so `妹とキスとメガネさん2` keeps its 2 and places nothing; that is chosen,
because `あやめ14` is a name. They cannot see a reading gloss inside a designation, so
`百合(レズ)合コンと迷い込んだノンケの娘` is not recognised as its work's title written another way.
And a record that cut its designation short mid-word, `その後~「瞳`, yields the fragment as the name.
What catches each of these is a person reading a work page, or the naming run declining an item it
cannot make sense of.
