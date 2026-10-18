#!/usr/bin/env python3
"""The patterns every web source shares, in one place.

WHY. A census on 2026-08-10 found `<title>` written two ways in four files and `og:title` written
two ways in four more, along with the RSS and Atom item wrappers in five. None of those is a fact
about a particular platform; they are facts about HTML and about the two feed formats, and a second
spelling of one is a place a fix lands once.

WHAT DOES NOT BELONG HERE. A selector naming one shop's markup: `data-e2e="eli"` is comici's,
`m-book-item__label` is BOOK☆WALKER's, `/atom/series/` is gigaviewer's. Those are facts about that
source and belong to its adapter, one home each. Folding them together would put four shops'
markup in a file none of them owns, which is the false consolidation this project warns about.
"""
import re
from html import unescape as _unescape

#: The document title. Two spellings were in use, `(.*?)` and `([^<]*)`, which differ only on a
#: title containing a newline. The lazy form handles both.
TITLE = re.compile(r"<title>(.*?)</title>", re.S)

#: Open Graph title. Two spellings were in use, one requiring the attributes in a fixed order. The
#: tolerant form matches both, because a page that reorders its attributes has not changed its
#: title.
OG_TITLE = re.compile(r'<meta[^>]+property="og:title"[^>]+content="([^"]*)"')

#: RSS and Atom, whose wrappers differ and whose contents this does not interpret.
RSS_ITEM = re.compile(r"<item>(.*?)</item>", re.S)
ATOM_ENTRY = re.compile(r"<entry>(.*?)</entry>", re.S)

#: A link, and an image's alternative text.
ANCHOR = re.compile(r"<a\b[^>]*>(.*?)</a>", re.S)
ALT = re.compile(r'alt="([^"]*)"')

#: A definition list pair, which two catalogues use for their bibliographic fields.
DT_DD = re.compile(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", re.S)

#: A PAGE'S OWN DESCRIPTION, `og:description`, which is where a platform puts a synopsis or, for a
#: prize entry, the citation.
DESCRIPTION = re.compile(r'<meta\b(?=[^>]*\bproperty="og:description")[^>]*\bcontent="([^"]*)"')
#: The rank a prize citation closes on.
_RANK = r"(?:準大賞|大賞|佳作|期待賞|準入選|入選|奨励賞|特別賞)"
#: A PRIZE CITATION, in the two forms the platforms write it. Opening the description, as
#: となりのヤングジャンプ and くらげバンチ do: `ヤングジャンプ新人漫画大賞#039 準大賞+…`,
#: `COMITIA153「4時間スピード漫画賞」期待賞`, `第３回大波賞「佳作」受賞作品。`. Or bracketed after the
#: title's own sentence, as ヤンマガWeb does: `TITLE。【ちばてつや賞ヤング部門第88回佳作】…`. A synopsis
#: mentioning a prize later on is neither.
CITATION = (re.compile(r"^[^。]{0,60}?賞[^。]{0,24}?" + _RANK),
            re.compile(r"【[^】]{0,40}?賞[^】]{0,24}?" + _RANK + r"[^】]{0,12}】"))
#: How far into a description the bracketed form may sit: past the title's own sentence, no further.
CITATION_WITHIN = 100


def citation(html):
    """The prize citation a page gives as its description, or None."""
    m = DESCRIPTION.search(html or "")
    text = _unescape(m.group(1)).strip() if m else ""
    head = text[:CITATION_WITHIN]
    if CITATION[0].search(text):
        return text[:200]
    b = CITATION[1].search(head)
    return b.group(0) if b else None


#: The address a page says it lives at, in either attribute order.
CANONICAL = re.compile(r'<link\b(?=[^>]*\brel="canonical")[^>]*\bhref="([^"]+)"')


def canonical(html):
    """The page's own canonical address, or None. A fetch that followed a redirect has the page
    without knowing where it ended up; the page says so itself."""
    m = CANONICAL.search(html or "")
    return m.group(1) if m else None
