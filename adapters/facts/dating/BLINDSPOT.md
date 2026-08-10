# What `facts/dating` cannot see

It holds the terms the `date_basis` field can take and what each one means. It does not decide which
term a row gets, and every way that decision is wrong is invisible here.

## A term is only as good as the capture that assigns it

`no-print-edition` means a shop states 底本発行日 on none of the volumes it holds under an imprint.
That is a fact about what one shop published, and it is read as a fact about the book. A shop that
stopped transcribing print dates in 2019 would move works into this term with nothing here noticing,
because the term's meaning has not changed and its population has.

## A silence that is explained is still a silence

Five of the nine terms say why there is no date. Telling them apart was worth doing, and none of
them produces a date. A reader who sees `no-print-edition` and a reader who sees `no-date-attested`
both see a work with no publication date, and the difference is only in what somebody should do
next.

## The fallback answers confidently

A term this table has never heard of gets the sentence for `no-date-attested`, which says no source
stated a date and none said why. If a capture invents a term and forgets to add it here, its rows
read as unexplained silences and the sentence is wrong in the confident direction. The test asserts
the unknown term gets no venue type, which is the part that would otherwise be a claim about a venue
nobody looked at.

## `dated` is a property of the term and not of the row

`chapter-serial` dates a row from 更新, the day the latest chapter went up, which is the most recent
publication rather than the first. The term is marked as dating the row because it produces a date,
and nothing here says that date answers the question a reader is asking.

## It says nothing about which date wins

A work can carry a delivery date and a stated printing. Which one a row shows is `delivery.promote`
and the DEFINITIONS §6 ruling behind it, and the refusal that protects a printing lives there.
