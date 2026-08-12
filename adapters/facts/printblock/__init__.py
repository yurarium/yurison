#!/usr/bin/env python3
"""What a print block on a series row stands for, for the passes that count names off it.

A BLOCK IS A RUN AND A RUN CAN BE SEVERAL CATALOGUE RECORDS. build.py draws one block per print
run, and MADB files one run under a second heading whenever the spine changes: 捏造トラップ holds
volumes 1, 2, 3 and 5 and 捏造トラップ : NTR holds 4 and 6. The block shows the primary record's
publisher, line and dates, because a work page has one place to show them.

THE PASSES THAT COUNT ARE NOT THE PAGE. Three of them walk `series[].print[]` and take the names
off it: the publisher name map, the imprint census that measures which years a spelling covers, and
the assembly of the publisher pages. Every one of them was measuring one record per block, and when
the blocks began folding they lost the records folded in. That was not cosmetic: 36 line names
dropped out of the name map while the volume rows went on drawing them from their own works.json
records, so `裏サンデー女子部` reached a reader as `????-???[?]`, and two houses kept a link to a
page that no longer had anything to build itself from.

So `folded_names` carries what each folded record states, and everything that counts goes through
`parties`. What a block SHOWS is a choice about a page; what it STANDS FOR is a fact about the
corpus, and the two stopped being the same thing when runs began to merge.
"""

#: The fields a folded record carries forward: who it names, and when it ran.
CARRIED = ("publisher", "distributor", "imprint", "first", "last")


def folded_names(blocks):
    """The `folded_names` entry for a list of already-built blocks, or `[]` where there is one.

    Written from the blocks rather than from the records, so the fields are the ones the passes
    read and are normalised exactly as `_print_block` normalises them.
    """
    out = []
    for b in blocks[1:]:
        got = {f: b[f] for f in CARRIED if b.get(f)}
        if got:
            out.append(got)
    return out


def parties(block):
    """Each publishing party a block stands for, one entry per catalogue record behind it.

    The block itself comes first, whole, so a caller reading anything beyond `CARRIED` off the
    first entry still finds it. The rest are the folded records, and each states its own dates: an
    imprint's span is measured from the record that carries the imprint, not from whichever record
    happened to name the run.
    """
    yield block
    for extra in block.get("folded_names") or ():
        yield extra
