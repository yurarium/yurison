#!/usr/bin/env python3
"""One comparison form for "is this the same title, or the same platform".

WHY THIS EXISTS. Two copies of this function drifted apart. They were byte-identical, comment and
all, except that `adapters/coverage_union.py` stripped `+` and `adapters/webcomics/coverage.py`
did not. Nobody decided that; one of them was edited and the other was not.

WHY `+` IS KEPT. coverage_union applies this only to PLATFORM names, and there the plus is the
whole distinction: 少年ジャンプ+ is Shueisha's web platform and 少年ジャンプ is the print magazine.
花とゆめ+ likewise. Stripping it would have merged a platform with a magazine the moment a print
title entered the platform list, which nothing prevents. Measured across all 50 platform names
before the change: the grouping is identical either way today, so this removes a latent hazard
rather than fixing a live fault.

WHAT IS STRIPPED, and why each of them:

  zero-width and bidi controls   Web漫画アンテナ emits platform names carrying U+200E and U+200F,
                                 so 竹コミ compared unequal to 竹コミ and one platform appeared as
                                 two. Invisible in a diff, which is why it is stripped rather than
                                 spotted.
  NFKC                           full-width and half-width are presentation, and databases differ
  case                           likewise
  whitespace                     including the internal kind: 百合 の 花 is 百合の花
  decorative brackets and marks  「」『』【】 and the ordinary punctuation around a title vary
                                 between sources and never mean a different work

Anything not in that list is CONTENT, and a different word means a different work.
"""
import re
import unicodedata

# Invisible characters that make two identical strings compare unequal.
INVISIBLE = re.compile(r"[​-‏‪-‮﻿]")

# Presentation, never identity. Note the absence of `+`, which is deliberate and load-bearing:
# see the module docstring. Adding it back merges 少年ジャンプ+ with 少年ジャンプ.
DECORATION = re.compile(r"""[\s\-.=、。･・!?,:;'"“”‘’()\[\]{}「」『』【】〈〉《》〔〕~〜_/\\|*&#@]""")


def norm(s):
    """The comparison form. Loose about presentation, strict about content."""
    s = INVISIBLE.sub("", s or "")
    s = unicodedata.normalize("NFKC", s)
    return DECORATION.sub("", s.strip().lower())
