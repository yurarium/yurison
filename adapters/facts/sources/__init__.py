#!/usr/bin/env python3
"""Hosts that are not a publication source.

WHY THIS IS A FACT. DEFINITIONS §6 turns on a work being published somewhere and REQUIREMENTS §5
says a promotional sample is not a release, so whether a host can supply a chapter at all is one
question. It was answered in three places: a target list said whether to fetch, `build.PROMO_HOSTS`
said whether to count the rows once fetched, and `serialisation/confirm` asked build.py so a search
would not anchor a work to one.

THE LAYER WAS WRONG. A host we will not publish from should not be INGESTED, and holding the rows
to decline them later makes every later pass carry the exception. So nothing is fetched, nothing is
stored, and `check.inv_no_record_comes_from_a_host_that_is_not_a_source` fails if a record ever
carries one again.

A LEAD IS SOMETHING ELSE, which is why this is a list and not a deletion. A search still returns
these addresses however little of them we store, so `serialisation/confirm` asks here too. The two
questions are whether this may become a record and whether it may anchor a work.

WHAT IS RECORDED IS THE EXCLUSION, not the site. Enough to keep a later coverage pass from putting
the host forward as a new source to consider, and no more.
"""

#: `host: what it is`. One short clause, because the entry exists to settle the question and not to
#: describe the site.
NOT_A_PUBLICATION_SOURCE = {
    "ddnavi.com": "a books news site running 試し読み of finished books. Excluded 2026-08-10.",
}


def not_a_source(url):
    """The reason `url`'s host is not a publication source, or None if it may be one.

    SUBSTRING, matched against the whole address, because callers hold a URL rather than a parsed
    host and one site reaches us under more than one spelling.
    """
    return next((why for host, why in NOT_A_PUBLICATION_SOURCE.items() if host in (url or "")), None)


def hosts():
    """Every host that may not supply a record, for a caller filtering a list of addresses."""
    return tuple(NOT_A_PUBLICATION_SOURCE)


if __name__ == "__main__":
    for h, why in NOT_A_PUBLICATION_SOURCE.items():
        print(f"{h}  {why}")
