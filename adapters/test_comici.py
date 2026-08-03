#!/usr/bin/env python3
"""comici.py: reading episodes and their access terms off a Comici listing.

Access terms are the one field a reader acts on, and the project counts rate-limited free as free
because it is free to a reader willing to wait. The precedence below encodes that: paid wins over
everything, and the two ticket kinds are distinct because they mean different waits.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import comici


def block(title, y, m, d, marker=""):
    return (f'<div data-e2e="eli">{marker}'
            f'<span data-e2e="eliTitle">{title}</span>'
            f'<span class="series-eplist-item-meta-date">{y}/{m}/{d}</span></div>')


def main(s):
    s.check(not comici.is_comici("<html>nothing here</html>"), "a foreign page is not Comici")
    s.check(comici.is_comici(block("x", 2026, 8, 3)), "a Comici page is recognised")

    # Dates are zero-padded on the way in, or they sort as strings incorrectly.
    rows = comici.rows(block("第1話", 2026, 8, 3))
    s.eq(len(rows), 1, "one block yields one row")
    if rows:
        s.eq(rows[0]["updated"], "2026-08-03", "a single-digit month and day are padded")
        s.eq(rows[0]["title"], "第1話", "the title is taken from the title element")

    # Access precedence. Paid must beat a ticket marker on the same block: a chapter that costs
    # coins is not free-timed just because the series is ticket-eligible.
    paid = comici.rows(block("a", 2026, 1, 1, '<i data-e2e="eliCoinIcon"></i>'))
    s.eq(paid[0].get("access_modes"), ["purchase"], "a coin icon means purchase")

    wf = comici.rows(block("b", 2026, 1, 1, '<i data-e2e="eliWfIcon"></i>'))
    s.eq(wf[0].get("access_modes"), ["free-timed"], "a common ticket is free-timed")
    s.check("共通チケット" in (wf[0].get("access_note") or ""),
            "and the note says which ticket, because the waits differ")

    iff = comici.rows(block("c", 2026, 1, 1, '<i data-e2e="eliIfIcon"></i>'))
    s.check("作品チケット" in (iff[0].get("access_note") or ""),
            "a work ticket is named distinctly from a common one")

    free = comici.rows(block("d", 2026, 1, 1, '<i data-e2e="eliFreeBadge"></i>'))
    s.eq(free[0].get("access_modes"), ["free"], "a free badge means free")

    # Silence is a state. A block stating nothing must not be guessed at as free.
    quiet = comici.rows(block("e", 2026, 1, 1))
    s.check("access_modes" not in quiet[0],
            "a block that states no access terms records none, rather than assuming free")

    # Order is the platform's, because chapter order carries meaning we do not re-derive.
    many = comici.rows(block("1", 2026, 1, 1) + block("2", 2026, 1, 2) + block("3", 2026, 1, 3))
    s.eq([r["title"] for r in many], ["1", "2", "3"], "rows keep the platform's order")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "comici"))
