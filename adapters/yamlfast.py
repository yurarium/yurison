#!/usr/bin/env python3
"""Read YAML with libyaml where it is installed, decided in one place for the whole project.

WHY THIS EXISTS. PyYAML ships two parsers. The pure-Python one is the default, and the C one bound
to libyaml is opt-in per call through a `Loader=` argument nothing here was passing, so every read
in this repository went through the slow one. `data/` and the CI workflows come to 3,646 YAML files
and 34.4 MB, and one pass over them costs about 41 seconds pure against 6 with libyaml. `./build.py`
reads the tree several times over and went from 207 seconds to 46 on the day this was turned on,
producing byte-identical output.

WHY NOT A LOADER ARGUMENT AT EACH CALL. There are 200 `yaml.safe_load` sites across `build.py`,
`check.py` and `adapters/`. Two hundred arguments is 200 chances to omit one, and an omission is
invisible: the read still returns the right answer, only slower, so nothing fails and nobody looks.

WHY NOT A WRAPPER MODULE THAT CALL SITES IMPORT. `yamlio.load(path)` beside `yaml.safe_load` would
be a SECOND producer of the same fact, which is the shape STANDING-INSTRUCTIONS §3 attributes seven
shipped bugs to. `yaml.safe_load` is already the project's single answer to "how do we read YAML",
written 200 times and never varied. The fix belongs behind that name, not next to it.

So this module rebinds `yaml.safe_load` and `yaml.safe_load_all` to the same call with the C loader
supplied. Every existing site gets it, and so does every site written afterwards, including one
written by somebody who has never read this file.

WHAT IT DELIBERATELY LEAVES ALONE.

`yaml.SafeLoader` keeps its meaning. Rebinding the CLASS would have covered these two functions and
`yaml.load(s, yaml.SafeLoader)` in one line, and it would also have changed what the name means for
any other library in the process, including one that subclasses it. Nothing here names the class,
so the narrower binding costs nothing.

The dumper is untouched. `yaml.dump` and `yaml.safe_dump` have 26 call sites, and their output is
COMMITTED DATA: libyaml's emitter breaks lines and quotes scalars at slightly different points, so
swapping it would rewrite files across `data/` for no gain on a path that is not the cost. Writing
happens once per fetch; reading happens on every build, deploy, gate and test.

FALLING BACK. libyaml is a compiled extension and a machine can be without it. `install()` asks
PyYAML (`yaml.__with_libyaml__`) instead of assuming, and where the answer is no it leaves the
module exactly as it found it. The project then runs at the old speed, which is the behaviour
everything had before this file existed. `YURI_YAML=python` hides libyaml on a machine that has
it, so that branch can be run on demand and not only reasoned about.

THE PROOF THAT THE TWO AGREE. A sample would have left the answer as a probability, so both loaders
were run over all 3,646 YAML files in the repository, 3,643 under `data/` and three CI workflows,
and the results compared on type identity and key order instead of with `==`, since `True == 1` and
`1 == 1.0` would let a real change through. Zero documents differed. What that pass covered:

  35,399 dates       `published: 2025-09-27` stays a `datetime.date` under both. The two loaders
                     share one `SafeConstructor` and one `Resolver`, so the timestamp rule is
                     literally the same code; only the scanner and parser below it differ.
  304,655 strings    holding non-ASCII, identical under both, including combining marks and
                     characters outside the basic plane.
  59 duplicate keys  58 in `data/names/curated.yaml` and 1 in `data/queue/serialisation-joins.yaml`.
                     Both loaders keep the last and drop the earlier silently, and the resulting
                     dicts match key for key in insertion order.
  0 explicit tags    Every tag in the corpus is one of the eight the resolver assigns implicitly.
                     Nothing here writes `!thing`, so no constructor lookup can diverge.

Two constructed inputs DO behave differently, neither of which occurs in any file here and neither
of which changes a value:

  a tab inside a plain scalar   `a: one<TAB>two`. libyaml accepts it, the pure scanner raises. The
                               spec is on libyaml's side. Nothing can produce it in any case, as
                               `yaml.dump` quotes any scalar holding a tab.
  a lone surrogate escape      `a: "\\ud800"`. The pure loader builds the unpaired surrogate,
                               libyaml refuses it. Refusing is the better answer, since such a
                               string cannot be encoded to UTF-8 and would fail at the point of
                               writing rather than at the point of reading.

Both differences are about which malformed input is REJECTED. On every input either loader accepts,
they produce the same object.

WHAT IS LEFT, so the next person to profile a build starts where this one stopped. libyaml replaces
the scanner and the parser. It does NOT replace the constructor or the resolver, which stay pure
Python and which the C parser calls back into for every node: 7.06 million `Resolver.resolve` calls
in one build. And `build.py` parses 22,728 documents from 3,610 distinct files, so the same file is
read six times over on average and twelve times at worst, which is 24.8 of the 34.4 seconds the
build now spends inside `yaml.safe_load`. `adapters/captures.py` already solves that repeat for the
queue captures. Whoever extends it to `data/source/` has one thing to fix first: its JSON sidecar is
written with `default=str`, which turns a `datetime.date` into a string. Today's callers all compare
that field as text so nothing is wrong, and 35,399 dates would go through it.

Usage: `import yamlfast` where `adapters/` is on the path, `from adapters import yamlfast` where the
repository root is, before the first read. Nothing else. `test_yamlfast.py` reparses real files from
`data/` both ways on every `./test.py`, so the agreement above is measured again and not recalled.
"""
import os

import yaml

# The state lives on the `yaml` module and not in a global here, because this file can be imported
# under two names in one process: `import yamlfast` when adapters/ is on the path, and
# `from adapters import yamlfast` when the repository root is. Python builds a separate module
# object for each, so a global would give the second copy a wrong idea of what the first did, and
# `uninstall` would restore a function that was already a replacement.
_MARK = "_yamlfast_replaced"


def _original(name):
    """PyYAML's own function, whether or not a copy of this module has already been through."""
    fn = getattr(yaml, name)
    return getattr(fn, _MARK, fn)


def available():
    """Whether the C parser can be used here.

    `YURI_YAML=python` turns it off. That is not a preference knob, it is how the fallback gets
    exercised: libyaml is present on every machine this has run on, so without a way to hide it
    the branch that has to work when it is missing is never taken, and a fallback nobody has run
    is a fallback nobody knows about. `YURI_YAML=python ./check.py --gate` takes it.
    """
    if os.environ.get("YURI_YAML") == "python":
        return False
    return bool(getattr(yaml, "__with_libyaml__", False)) and hasattr(yaml, "CSafeLoader")


def parser():
    """Which parser `yaml.safe_load` uses right now: "libyaml" or "python"."""
    return "libyaml" if hasattr(yaml.safe_load, _MARK) else "python"


def install():
    """Point `yaml.safe_load` at the C parser. Idempotent, and a no-op without libyaml.

    Returns the parser now in effect, so a caller reporting the state has a fact and not a guess.
    """
    if not available() or parser() == "libyaml":
        return parser()

    def safe_load(stream):
        if isinstance(stream, (str, bytes)) and not os.environ.get("YURI_NO_YAML_MEMO"):
            return _memo(stream)
        return yaml.load(stream, Loader=yaml.CSafeLoader)

    def safe_load_all(stream):
        return yaml.load_all(stream, Loader=yaml.CSafeLoader)

    for fn, name in ((safe_load, "safe_load"), (safe_load_all, "safe_load_all")):
        setattr(fn, _MARK, _original(name))
        fn.__doc__ = _original(name).__doc__
        setattr(yaml, name, fn)
    return parser()


#: One parse per distinct document IN ONE RUN, keyed on the text itself.
#:
#: A BUILD READS THE SAME FILE SEVERAL TIMES. 22,774 `safe_load` calls cost 55 of the 76 seconds a
#: profiled build takes, and most of them re-parse a document parsed a moment earlier by a different
#: stage. Keyed on the text and not on a path, so a caller that read the file itself gets the same
#: answer as one that read it again.
#:
#: EVERY CALLER GETS ITS OWN OBJECT. Handing back the cached document would let one stage's mutation
#: reach another's read, which is the worst kind of fault to go looking for. The cache holds a
#: pickle and each call unpickles it, which is a deep copy at about a twenty-fourth of the cost of
#: re-parsing, and it round-trips a `datetime.date` exactly where JSON cannot hold one at all.
#:
#: IT IS A PROCESS'S MEMORY AND NOT A FILE. Nothing is written to disk, so there is no invalidation
#: to get wrong: a run that reads an edited file reads the edit, because the text is the key.
_PARSED = {}

#: Documents kept before the cache is emptied. A build holds about 5 MiB at 3,646 files; the cap is
#: there so a caller streaming thousands of unrelated documents cannot grow it without bound.
MEMO_LIMIT = 20000


def _memo(stream):
    import hashlib
    import pickle
    raw = stream.encode("utf-8") if isinstance(stream, str) else stream
    key = hashlib.sha256(raw).digest()
    blob = _PARSED.get(key)
    if blob is None:
        doc = yaml.load(stream, Loader=yaml.CSafeLoader)
        try:
            blob = pickle.dumps(doc, protocol=5)
        except Exception:                                               # noqa: BLE001
            # A DOCUMENT THAT WILL NOT PICKLE IS RETURNED AND NOT REMEMBERED, which is the parser's
            # behaviour before this existed. Nothing in this corpus reaches it; it is here because
            # a cache that raises on an unusual document would be worse than no cache.
            return doc
        if len(_PARSED) < MEMO_LIMIT:
            _PARSED[key] = blob
        return doc
    return pickle.loads(blob)


def forget():
    """Empty the memo. For a test that needs a parse to actually happen."""
    _PARSED.clear()


def uninstall():
    """Put PyYAML back as it was. For the test, which has to be able to read both ways."""
    for name in ("safe_load", "safe_load_all"):
        setattr(yaml, name, _original(name))
    return parser()


install()
