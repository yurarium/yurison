#!/usr/bin/env python3
"""What counts as a platform calling a work yuri. One vocabulary, because it decides admission.

WHY THIS IS A FACT AND WHY IT MATTERS MOST. DEFINITIONS decides what the database holds, and a
platform's own label is one of the signals it decides on. The vocabulary lived in three files,
`pixivcomic/releases`, `kadokomi/releases` and `kadokomi/confirm`, so three adapters could have
drifted apart about what admits a work and the drift would have shown as one platform quietly
holding a work another dropped.

A census on 2026-08-10 found it. It was not on the inventory of ten facts, which is the argument
for looking instead of listing.

WHAT IT DOES NOT DECIDE. Whether the work is admitted, which is DEFINITIONS section 6 and weighs
several signals; and whether the label is trustworthy on a given platform, which is that adapter's
business. This says only which strings are a platform saying "yuri".
"""

#: The labels a Japanese platform uses. 百合 is the genre's name; GL and ガールズラブ are the
#: English and its transliteration, used interchangeably in shop taxonomies.
#:
#: DELIBERATELY NARROW. A broader net (百合姫, ガール, GIRLS) would catch a magazine name and a
#: publisher's line rather than a genre label, and admitting on a magazine name is a different
#: argument from admitting on a genre tag. If a platform is found using another word for the genre,
#: it belongs here with the page that showed it.
TAGS = frozenset({"百合", "GL", "ガールズラブ"})


def is_yuri_label(tag):
    """Whether one tag is a platform calling the work yuri."""
    return str(tag or "").strip() in TAGS


def labels_in(tags):
    """Every yuri label in an iterable of tags, in the order given."""
    return [t for t in (tags or []) if is_yuri_label(t)]
