#!/usr/bin/env python3
"""yamlfast.py: the C parser reads what the Python parser read, on this repository's own files.

WHY THIS RUNS ON REAL DATA. A constructed document proves the two loaders agree about a shape
somebody thought of. The classes that would hurt here are the ones the pipeline actually writes:
`published: 2025-09-27` held as a `datetime.date`, Japanese titles, and the duplicate keys
`data/names/curated.yaml` has carried more than once. So the sample below comes out of `data/`,
weighted towards the big files, and the comparison is on type identity instead of `==`, because
`True == 1` and `1 == 1.0` would let a real change through.

The constructed cases are kept ALONGSIDE the sampled ones and not instead of them, because a
corpus can lose a shape. The day somebody de-duplicates `curated.yaml`, the sampled half of the
duplicate-key check goes quiet and reports clean forever; the constructed half cannot.

`--all` sweeps every YAML file in the repository, which takes about four minutes. The sample runs
by default so that `./test.py` stays under half a minute.
"""
import datetime
import importlib
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import yaml
import yamlfast

ROOT = pathlib.Path(__file__).resolve().parents[1]


def strict(a, b, path="$"):
    """The first place two documents stop being the same object shape, or None."""
    if type(a) is not type(b):
        return f"{path}: {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        if list(map(repr, a)) != list(map(repr, b)):
            return f"{path}: keys differ or are ordered differently"
        for k in a:
            d = strict(a[k], b[k], f"{path}[{k!r}]")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = strict(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if a == b else f"{path}: {a!r} vs {b!r}"


HAVE_C = hasattr(yaml, "CSafeLoader")


def both(text):
    """The document as each parser builds it, named explicitly so the module's binding cannot
    quietly make this a comparison of one parser with itself."""
    pure = yaml.load(text, Loader=yaml.SafeLoader)
    return pure, (yaml.load(text, Loader=yaml.CSafeLoader) if HAVE_C else pure)


def classes(doc, seen):
    """Count the value types in a document, so the sample can be shown to contain what matters."""
    seen[type(doc).__name__] = seen.get(type(doc).__name__, 0) + 1
    if isinstance(doc, dict):
        for k, v in doc.items():
            classes(k, seen)
            classes(v, seen)
    elif isinstance(doc, list):
        for v in doc:
            classes(v, seen)
    elif isinstance(doc, str) and not doc.isascii():
        seen["non-ascii"] = seen.get("non-ascii", 0) + 1


def duplicate_keys(text, loader):
    """Mapping keys this document loses to a later key of the same name.

    Counted on the node tree because construction is where the loss happens: by the time
    SafeConstructor has built a dict, the earlier key is gone and nothing can see it went.
    """
    n, stack = 0, list(yaml.compose_all(text, Loader=loader))
    while stack:
        node = stack.pop()
        if isinstance(node, yaml.MappingNode):
            keys = [k.value for k, _ in node.value]
            n += len(keys) - len(set(keys))
            for k, v in node.value:
                stack += [k, v]
        elif isinstance(node, yaml.SequenceNode):
            stack += node.value
    return n


# Named because the duplicate keys are here. `curated.yaml` has carried several, the file's
# behaviour on them is load-bearing (YAML keeps the last), and it is the largest store the naming
# passes write. Missing is tolerated: the constructed duplicate-key case below does not need it.
AWKWARD = ROOT / "data" / "names" / "curated.yaml"


def sample(budget=600_000):
    """A spread of real files inside a byte budget, plus the one the awkward cases live in.

    Budgeted because the point is to run on every `./test.py`, and the pure parser costs about a
    second and a quarter per megabyte. The full 34 MB sweep is `--all`.

    Half the budget goes to the largest files that fit, where the long records and the odd dates
    are, and half to a stride across the rest, so a fault confined to the small per-source files
    is still reachable.
    """
    files = sorted((p for p in (ROOT / "data").rglob("*.yaml") if p.is_file()),
                   key=lambda p: p.stat().st_size)
    picked, spent = ([AWKWARD] if AWKWARD.exists() else []), 0
    for p in reversed(files):
        n = p.stat().st_size
        if p not in picked and spent + n <= budget // 2:
            picked.append(p)
            spent += n
    for p in files[::max(1, len(files) // 40)]:
        n = p.stat().st_size
        if p not in picked and spent + n <= budget:
            picked.append(p)
            spent += n
    return picked


def main(s):
    # ── The swap happened, or this machine has no libyaml and said so ──────────────────────────
    pristine = yamlfast._original("safe_load")
    if yamlfast.available():
        s.eq(yamlfast.parser(), "libyaml", "importing yamlfast selects the C parser")
        s.ne(yaml.safe_load, pristine, "yaml.safe_load is no longer PyYAML's own function")
        s.eq(yamlfast.install(), "libyaml", "installing twice is a no-op, not a second wrapper")
        s.eq(yamlfast._original("safe_load"), pristine,
             "and a second install still knows what PyYAML's own function was")
    else:
        # Reached with `YURI_YAML=python`, and on any machine whose PyYAML was built without the
        # extension. The fallback is the point of the branch, so it is asserted and not skipped.
        s.eq(yamlfast.parser(), "python", "without libyaml the module leaves PyYAML alone")
        s.eq(yaml.safe_load, pristine, "and safe_load is PyYAML's own")

    # `uninstall` then `install` must land back where it started, because the comparison below
    # reads the same bytes both ways and would be comparing one parser with itself otherwise.
    was = yamlfast.parser()
    s.eq(yamlfast.uninstall(), "python", "uninstall puts PyYAML back")
    s.eq(yaml.safe_load, pristine, "and the original function is restored")
    yamlfast.install()
    s.eq(yamlfast.parser(), was, "and install returns it to where the import left it")

    # ── The fallback, exercised rather than asserted in a branch that never runs here ──────────
    # libyaml is a compiled extension and a machine can be without it. The build must then run at
    # the old speed and not fail to import, so the absence is simulated and the module re-imported
    # under it. Taking the machine's word for the branch it does not take is how a fallback rots.
    for hide in ("attribute", "environment"):
        had, env = yaml.__with_libyaml__, os.environ.get("YURI_YAML")
        try:
            yamlfast.uninstall()
            if hide == "attribute":
                yaml.__with_libyaml__ = False       # PyYAML built without the extension
            else:
                os.environ["YURI_YAML"] = "python"  # the same machine, told to pretend
            cold = importlib.reload(yamlfast)
            s.eq(cold.available(), False, f"with libyaml hidden by {hide}, the C parser is off")
            s.eq(cold.parser(), "python", f"and the import leaves PyYAML's own reader ({hide})")
            s.eq(cold.install(), "python", f"and install is a no-op instead of an error ({hide})")
            s.eq(yaml.safe_load("published: 2025-09-27\n"),
                 {"published": datetime.date(2025, 9, 27)},
                 f"and yaml.safe_load still reads a date ({hide})")
        finally:
            yaml.__with_libyaml__ = had
            os.environ.pop("YURI_YAML", None)
            if env is not None:
                os.environ["YURI_YAML"] = env
            importlib.reload(yamlfast)
        s.eq(yamlfast.parser(), was, f"and restoring libyaml puts the fast parser back ({hide})")

    # ── The value classes that would hurt, constructed so the corpus cannot take them away ─────
    a, b = both("published: 2025-09-27\n")
    s.eq(type(a["published"]), datetime.date, "a plain date loads as a date, not a string")
    s.eq(strict(a, b), None, "and both parsers agree that it is one")

    a, b = both("at: 2025-09-27T13:04:05+09:00\n")
    s.eq(type(a["at"]), datetime.datetime, "a timestamp with an offset loads as a datetime")
    s.eq(strict(a, b), None, "and both parsers agree")

    a, b = both("a: '2025-09-27'\n")
    s.eq(type(a["a"]), str, "a quoted date stays a string")
    s.eq(strict(a, b), None, "under both parsers")

    a, b = both("k: first\nk: second\nk: third\n")
    s.eq(a["k"], "third", "a duplicate key keeps the last, which curated.yaml relies on")
    s.eq(strict(a, b), None, "and both parsers drop the same two")

    a, b = both("作者: ゆりのゆかい\n")
    s.eq(strict(a, b), None, "a Japanese key and value survive both parsers unchanged")

    a, b = both("a: 0x1f\nb: 1_000\nc: yes\nd: ~\ne: .inf\nf: 1:30\n")
    s.eq(strict(a, b), None, "so do the implicit int, bool, null and float resolutions")

    # ── The same question asked of files the pipeline really wrote ─────────────────────────────
    files = (sorted(p for p in ROOT.rglob("*.yaml") if ".git" not in p.parts)
             if "--all" in sys.argv else sample())
    seen, diffs, dup_files, dup_keys = {}, [], 0, 0
    for p in files:
        text = p.read_text()
        x, y = both(text)
        d = strict(x, y, p.name)
        if d:
            diffs.append(d)
        classes(x, seen)
        n = duplicate_keys(text, yaml.SafeLoader)
        if n:
            dup_files += 1
            dup_keys += n
            if HAVE_C and duplicate_keys(text, yaml.CSafeLoader) != n:
                diffs.append(f"{p.name}: the two parsers count duplicate keys differently")

    s.eq(diffs, [], f"the two parsers agree on all {len(files)} sampled files")
    # Without the C extension there is no second parser and the line above compared the pure one
    # with itself, which is the vacuous green this project keeps meeting. Say so.
    s.check(HAVE_C, "PyYAML here carries CSafeLoader, so the comparison above had two parsers")

    # A sample that holds none of the awkward classes would agree trivially, so the sample itself
    # is asserted. §14b: a check whose subject filtered out every failing case reports clean.
    s.check(len(files) >= 40, f"the sample is worth running: {len(files)} files")
    s.check(seen.get("date", 0) > 100, f"and holds dates to get wrong: {seen.get('date', 0)}")
    s.check(seen.get("non-ascii", 0) > 100,
            f"and Japanese to get wrong: {seen.get('non-ascii', 0)} strings")
    print(f"          sampled {len(files)} file(s); "
          f"{seen.get('date', 0)} dates, {seen.get('non-ascii', 0)} non-ascii strings, "
          f"{dup_keys} duplicate key(s) in {dup_files} file(s)")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "yamlfast"))
