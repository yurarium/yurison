#!/usr/bin/env python3
"""The content-flag register, and the accounting that replaced a control nobody could observe.

COVERS = ['build.py']

A register was written from the first run and read by nothing, so five flagged works were published
while a file said they were not. These pin the shape of the remedy: flags are REPORTED rather than
obeyed, and the report has to agree with the register.
"""
import importlib.util
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
import testkit

ROOT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("buildmod", ROOT / "build.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def main(s):
    import os
    import yaml
    cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    try:
        reg = pathlib.Path(tmp) / "data" / "source" / "someplatform"
        reg.mkdir(parents=True)
        (reg / "withheld.yaml").write_text(yaml.safe_dump({
            "source": "someplatform",
            "works": [
                {"work_title": "報告のみ", "reason": "ratingLevel='adult'"},
                {"work_title": "実際に非公開", "reason": "reviewed", "withhold": True},
            ]}, allow_unicode=True))
        os.chdir(tmp)

        flags = b.content_flags()
        s.eq(len(flags), 2, "both entries are read as flags")

        # THE POLICY. A flag records and reports; it does not withhold by itself, because every
        # platform here is a commercial publisher's web arm.
        held = b.withheld_works()
        s.eq(len(held), 1, "only the entry marked withhold is withheld")
        s.check(any(v["title"] == "実際に非公開" for v in held.values()),
                "and it is the one that says so")
        s.check(not any(v["title"] == "報告のみ" for v in held.values()),
                "a flag without withhold does NOT hold a work back")

        # Both are still flags, so both must reach the report. This is the bit that failed before:
        # a work can be published and still owe an entry in the count.
        titles = {v["title"] for v in flags.values()}
        s.check("報告のみ" in titles, "a published flagged work is still reported")
        s.check("実際に非公開" in titles, "and so is a withheld one")

        for v in flags.values():
            s.check(v.get("reason"), f"{v['title']}: a flag carries its reason, or it cannot be reviewed")
            s.check(v.get("source"), f"{v['title']}: and names the source that raised it")

        # An empty register is the normal state and must not raise.
        (reg / "withheld.yaml").write_text(yaml.safe_dump({"source": "x", "works": []}))
        s.eq(b.content_flags(), {}, "an empty register yields no flags")
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    sys.exit(testkit.run(main, "content_flags"))
