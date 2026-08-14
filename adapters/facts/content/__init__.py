#!/usr/bin/env python3
"""Works a source flagged on content grounds, whether or not we act on the flag.

HOW THIS WENT WRONG, because the shape recurs. `adapters/kadokomi/confirm.py` has written
`data/source/kadokomi/withheld.yaml` since the first run, flagging works whose `ratingLevel` is
`adult`, its header saying they are not published. Nothing read the file. All five were live on the
public site, and no count anywhere said otherwise: a register nothing consumes is worse than no
register, because it reads as a control that is working.

WHAT THE POLICY IS, per the project owner. Every platform in this database is a commercial
publisher's own web arm, and a reader following a link to a serialisation there is not going to meet
unwanted pornographic content, certainly not up front. So a rating flag on such a platform withholds
nothing. It is RECORDED and REPORTED instead, so a less obvious future case cannot fall permanently
between the cracks. A flag withholds only where its entry says `withhold: true`, which is the
deliberate reviewed decision, and there are none today.

WHY IT IS A MODULE, STORE-PLAN §12. It was a function in `build.py` until the store's loader needed
the same register, and a rule asked twice becomes a module rather than a second copy. `build.py`
reports it, the store carries it, and `check.py` fails if a flag exists that nothing reports.
"""
import pathlib
import re

import yaml

#: Where a capture writes what it flagged. Every one of these files is a register some adapter
#: keeps; the name is the convention and the directory above it names the source.
REGISTER = "withheld.yaml"


def flags(root="data/source", key=None):
    """`{key: {title, reason, source, withhold}}` over every register under `root`.

    `key` FOLDS THE TITLE, and the caller supplies it because two callers fold differently on
    purpose. `build.py` keys on `norm_work` so a flag matches whatever spelling a platform used;
    the store keys on the title as written, because that is what it stores. Defaulting to one of
    them here would have made the other silently wrong.
    """
    out = {}
    for f in sorted(pathlib.Path(root).rglob(REGISTER)):
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for w in doc.get("works") or []:
            title = w.get("work_title")
            if not title:
                continue
            out[key(title) if key else title] = {
                "title": title, "reason": w.get("reason"),
                "source": doc.get("source") or f.parent.name,
                "withhold": bool(w.get("withhold"))}
    return out


# A TITLE THAT IS BOTH ADULT-MARKETED AND A COLLECTION. Both are required: えっち or セフレ alone
# appears in story titles, and アンソロジー alone is most of the anthologies the corpus carries.
# Together they describe how a volume is SOLD, which is the thing DEFINITIONS §7 turns on.
ADULT_MARKETED = re.compile(r"えっち|エッチ|セフレ|エロ|官能|18禁|R-?18|成人向")
COLLECTION_MARK = re.compile(r"アンソロジー|短編集|傑作選|オムニバス|読切集")


def marketing(titles, key=None):
    """`{key: {...}}` for adult-marketed collections among `titles`. Reported and published.

    一迅プラス publishes explicit yuri anthologies and exposes no rating field, so nothing else in
    the pipeline can see them. They are not pornography by §7's test and the project owner has
    decided they are safe to carry and to link to, which settles what happens to them. What was
    missing is that nothing would have SHOWN them: a category decided once and then invisible is
    how the withheld register went five works wrong for the life of the project.

    So they appear in the flag report with everything else, marked published, and a fourth arriving
    from a publisher nobody has thought about turns up in the same place rather than nowhere.

    TITLES RATHER THAN ROWS, §12. `build.py` passed its `series_rows` and the store's loader has
    the same titles in a different shape, so the argument is the thing the rule actually reads.
    """
    out = {}
    for title in titles:
        w = str(title or "")
        if ADULT_MARKETED.search(w) and COLLECTION_MARK.search(w):
            out[key(w) if key else w] = {
                "title": w, "source": "marketing signal",
                "reason": "adult-marketed collection; §7 explicit, not pornography",
                "withhold": False}
    return out
