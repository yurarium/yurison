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

    # THE WORK'S ADDRESS, off an episode page. Trimmed from
    # https://championcross.jp/episodes/c588f534a4870, fetched 2026-08-07: the work link appears
    # three times, an rss variant of it once, and two decoys sit on the same page.
    ep = ('<a href="/series/cbacd0530b63f">阿佐ヶ谷サキュバス同人物語</a>'
          '<a href="https://championcross.jp/series/cbacd0530b63f/rss">RSS</a>'
          '<a href="/series/list/up/1">作品一覧</a>'
          '<a href="/store_items/series/4333/1">単行本</a>')
    s.eq(comici.series_link(ep), "cbacd0530b63f",
         "the work hash is read from the episode page's own link to its series")
    # COUNTER-CASES. /series/list/up/1 is the platform's paging and /store_items/series/... is the
    # shop, and both would be read as a work by a rule that only looked for /series/.
    s.check(comici.series_link('<a href="/series/list/up/1">a</a>') is None,
            "the platform's own series listing is not a work")
    s.check(comici.series_link('<a href="/store_items/series/4333/1">a</a>') is None,
            "a shop path that contains /series/ is not a work")
    s.check(comici.series_link('<a href="/series/aaaaaaaaaaaaa">a</a>'
                               '<a href="/series/bbbbbbbbbbbbb">b</a>') is None,
            "two different series on one page name neither")
    s.check(comici.series_link("<html></html>") is None, "a page linking no series names none")
    s.eq(comici.series_address("championcross.jp", "cbacd0530b63f"),
         "https://championcross.jp/series/cbacd0530b63f", "the work's address on a comici host")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "comici"))
