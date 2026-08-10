#!/usr/bin/env python3
"""facts/sources: which hosts may not supply a record at all.

COVERS = ['adapters/facts/sources/__init__.py']

THE FAULT THIS IS FOR is answering one question in three places. A target list said whether to
fetch a host, `build.PROMO_HOSTS` said whether to count its rows once fetched, and
`serialisation/confirm` asked build.py so a search would not anchor a work to it. The rows were
ingested and then declined, so every later pass carried the exception.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import sources                                               # noqa: E402


def main(s):
    s.check(sources.not_a_source("https://ddnavi.com/anything/"),
            "a host on the list is refused, and the refusal carries its reason")
    s.check(not sources.not_a_source("https://comic.pixiv.net/works/10861"),
            "a publication platform is not")
    s.check(not sources.not_a_source(""), "and an empty address refuses nothing")
    s.check(not sources.not_a_source(None), "nor a missing one")

    # MATCHED ON THE WHOLE ADDRESS, because callers hold a URL and one site reaches us under more
    # than one spelling.
    s.check(sources.not_a_source("http://www.ddnavi.com/x"), "a subdomain is the same host")
    s.eq(sources.hosts(), tuple(sources.NOT_A_PUBLICATION_SOURCE),
         "and the host list is the keys of the table, so a caller filtering addresses agrees "
         "with a caller asking about one")

    # EVERY ENTRY SAYS WHY. The reason is what keeps a coverage pass from putting the host forward
    # again, and an entry with no reason records a membership nobody can argue with.
    for host, why in sources.NOT_A_PUBLICATION_SOURCE.items():
        s.check(host and "." in host, f"{host} is a host")
        s.check(len((why or "").strip()) > 20, f"{host} says what it is and when it was excluded")

    # THE TARGET LIST AGREES, which is the half a fact cannot enforce on its own: a host declared
    # here while `extract.yaml` still carries a live strategy would be refilled on the next run.
    # `check.inv_no_record_comes_from_a_host_that_is_not_a_source` is what asserts that, and this
    # pins the shape it reads so the two cannot drift apart silently.
    import yaml
    root = pathlib.Path(__file__).resolve().parents[3]
    doc = yaml.safe_load((root / "data" / "coverage" / "extract.yaml").read_text()) or {}
    live = [p for p in (doc.get("platforms") or [])
            if sources.not_a_source(str(p.get("host") or ""))
            and p.get("strategy") not in (None, "none", "no-response")]
    s.eq(live, [], "no excluded host carries an extraction strategy that would refill data/source")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "sources"))
