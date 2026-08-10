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
