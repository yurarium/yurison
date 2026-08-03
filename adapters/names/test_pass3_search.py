#!/usr/bin/env python3
"""pass3_search.py: the query pass 3 would issue, built from what earlier passes learned.

COVERS = ['adapters/names/pass3_search.py']

The lookup itself waits on a metered API key. The query construction does not, and it is the part
that decides whether a search is narrow enough to be worth a quota unit.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import pass3_search as p3


class Store:
    def __init__(self, records=None):
        self.records = {"authors": records or {}, "titles": {}}


def main(s):
    r = p3.SearchResolver()
    s.eq(r.name, "search", "the resolver names itself, so attempts are attributable")
    s.check("authors" in r.kinds and "titles" in r.kinds, "it handles both kinds of name")
    # §3.6: one query per name. The quota IS the pacing, so batching would defeat the point.
    s.eq(r.batch, 1, "one query per name, because the quota is the pacing")

    # A handle from pass 0 makes the narrowest query available, so it is used when present.
    with_handle = p3.SearchResolver(store=Store({"山田太郎": {"handles": ["yamada_taro"]}}))
    q = with_handle.query_for("authors", "山田太郎")
    s.check("yamada_taro" in q, "a known handle narrows the query")
    s.check("山田太郎" in q, "and the name is still in it")

    # Without a handle there is still a query, and it must not silently become empty.
    plain = p3.SearchResolver(store=Store())
    q2 = plain.query_for("authors", "山田太郎")
    s.check(q2 and "山田太郎" in q2, "a name with no handle still produces a query")

    q3 = p3.SearchResolver().query_for("titles", "百合の花")
    s.check(q3 and "百合の花" in q3, "a title query is built without any store at all")

    s.ne(q, q2, "the handle query differs from the fallback, or pass 0 bought nothing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.pass3_search"))
