#!/usr/bin/env python3
"""resolver.py: driving one source over one kind of name, without lying about what it said.

COVERS = ['adapters/names/resolver.py']

The attempt ledger is the point. NAMES-PLAN §4 says a source being down must never cost us a name,
and the only way to keep that true is to record nothing when nothing was said.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import resolver as rv


class Store:
    def __init__(self, todo):
        self.todo = todo
        self.records = {"authors": {}, "titles": {}}
        self.recorded, self.attempts = [], []

    def open_for(self, kind, names, source, provides):
        return list(self.todo)

    def record(self, kind, ja, **f):
        self.recorded.append((kind, ja, f))

    def attempt(self, *a, **k):
        self.attempts.append((a, k))

    def supplies(self, kind, ja, provides):
        # Whether the name is now RESOLVED, which is not the same as the source having replied.
        return any(x[1] == ja for x in self.recorded)

    def maybe_compact(self, n=None):
        pass

    def compact(self):
        pass


class Src:
    name, kinds, provides, batch = "src", ("authors",), "reading", 2

    def __init__(self, answers=None, boom=None):
        self.answers, self.boom, self.calls = answers or {}, boom, 0

    def lookup(self, kind, chunk, cache):
        self.calls += 1
        if self.boom:
            raise self.boom
        return {k: v for k, v in self.answers.items() if k in chunk}


class Cache:
    offline = False
    requests = 0


def main(s):
    # A resolver is only asked for the kinds it declares.
    st = Store(["a"])
    out = rv.drive(Src(), st, "titles", ["a"], Cache())
    s.check("skipped" in out, "a resolver is not asked for a kind it does not handle")

    # The happy path records what the source said.
    st = Store(["a", "b"])
    out = rv.drive(Src({"a": [{"reading": "エー"}]}), st, "authors", ["a", "b"], Cache())
    s.eq(out["asked"], 2, "both names were asked about")
    s.eq([ja for _, ja, _ in st.recorded], ["a"], "only the name with an answer is recorded")

    # A SOURCE BEING DOWN MUST COST NOTHING. Nothing is written, so the next run picks the names up
    # as though this one had not happened.
    st = Store(["a", "b", "c", "d"])
    src = Src(boom=rv.SourceUnavailable("503"))
    out = rv.drive(src, st, "authors", ["a", "b", "c", "d"], Cache())
    s.eq(st.recorded, [], "an outage records nothing at all")
    s.check(out["unavailable"], "and the outage is reported")
    s.eq(src.calls, 1, "and the run stops rather than hammering a source that is down")

    # OFFLINE IS NOT AN OUTAGE. A name whose response was never cached is simply not replayable, so
    # stopping at the first would abandon every cached name after it, which for a batch-of-one
    # source is nearly all of them.
    class Offline:
        offline = True
    st = Store(["a", "b", "c", "d"])
    src = Src(boom=rv.SourceUnavailable("not cached"))
    out = rv.drive(src, st, "authors", ["a", "b", "c", "d"], Offline())
    s.check(src.calls > 1, "offline carries on past a name that was never fetched")
    s.eq(st.recorded, [], "and still records nothing")
    s.check(out.get("not-cached"), "the uncached names are counted rather than lost silently")

    # THE SLOW LEAK. A source can answer with something it is not allowed to publish, leaving the
    # name exactly as unresolved as a miss. Counting that as a hit breaks nothing in the data, but
    # the name is never marked as asked, so every future run queries it again for ever and the cost
    # stops being bounded. An attempt must be recorded for every outcome that did not resolve.
    class PartialStore(Store):
        def supplies(self, kind, ja, provides):
            return False            # the source replied, but not with what it provides

    st = PartialStore(["a"])
    out = rv.drive(Src({"a": [{"en_candidate": "Some Title"}]}), st, "authors", ["a"], Cache())
    s.eq(out["partial"], 1, "an answer that does not resolve the name counts as partial")
    s.eq(out["hit"], 0, "and never as a hit")
    s.check(st.attempts, "an attempt is recorded, so the name is not queried for ever")

    st = PartialStore(["a"])
    out = rv.drive(Src({}), st, "authors", ["a"], Cache())
    s.eq(out["miss"], 1, "a source saying nothing is a miss")
    s.check(st.attempts, "and is also recorded as asked")

    # A limit is honoured, so a run can be bounded.
    st = Store(["a", "b", "c", "d"])
    out = rv.drive(Src(), st, "authors", ["a", "b", "c", "d"], Cache(), limit=2)
    s.eq(out["asked"], 2, "the limit bounds how many names are asked about")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.resolver"))
