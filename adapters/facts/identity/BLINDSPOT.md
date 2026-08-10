# What `facts/identity` cannot see

It mints an identifier for a work and re-finds that work later by an anchor. The promise is that an
identifier never moves and never disappears, and everything below is a way the JOIN behind it is
wrong while the promise is kept perfectly.

## An anchor is chosen because titles move, and anchors move too

A web work is anchored on its platform URL, unique across 985 of 993 works. A platform that
restructures its addresses breaks every anchor it owns at once, and the works come back as new. A
print work is anchored on a MADB C-number, which is stable until MADB reissues a record.

## The eight exceptions are the shape of the problem

Anthology stories share a container, so the URL is not unique for them and the folded story title
rides alongside. That is a title inside an anchor chosen because titles are unreliable, and it is
the smallest place where the design admits it has no better answer.

## A merge is recorded and a split is not

Two works that turn out to be one keep both identifiers: the retired one gains `merged_into` and
still resolves, so a published address keeps working. There is no matching machinery for one work
that turns out to be two. A wrong join erases a work and a wrong split invents one, so the file
holds the join it can undo and not the one it cannot.

## It answers nothing about whether two works are the same

`match_key` says whether two strings could name one thing. Whether they DO is a ruling somebody
records in `data/identity/`, and every number this module produces rests on those rulings being
right. Nothing here can find a wrong one: a work filed under another work's identifier is one row
and looks exactly like a correct one.

## Assignment is append-only, which means a mistake is permanent

An identifier minted for a row that should never have existed cannot be withdrawn, only retired. The
count of works is therefore a count of rows the corpus has ever admitted, and `admitted_by` is what
says why each one is there.
