#!/usr/bin/env python3
"""release.py: the bibliography's newest release replaces the held one only when it arrived whole."""
import io
import json
import pathlib
import sys
import tempfile
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from madb import release  # noqa: E402

COVERS = ["adapters/madb/release.py"]


def zipped(name, data):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{name}.json", data)
    return buf.getvalue()


def main(s):
    # GITHUB'S ANSWER, cut to the fields read. A release also carries Turtle files and twenty other
    # bulk files, and only the two the routes read are taken.
    doc = {"tag_name": "1.2.21", "published_at": "2026-10-16T06:30:53Z", "assets": [
        {"name": "metadata101_json.zip", "browser_download_url": "https://x/101j"},
        {"name": "metadata101_ttl.zip", "browser_download_url": "https://x/101t"},
        {"name": "metadata104_json.zip", "browser_download_url": "https://x/104j"},
        {"name": "metadata201_json.zip", "browser_download_url": "https://x/201j"}]}
    s.eq(release.latest(doc), ("1.2.21", "2026-10-16",
                               {"metadata101": "https://x/101j", "metadata104": "https://x/104j"}),
         "the tag, the day it was published, and the JSON assets of the two files the routes read")
    s.eq(release.latest({"tag_name": "9", "assets": []})[2],
         {"metadata101": None, "metadata104": None},
         "a release missing an asset says so rather than offering another file")

    s.eq(release.unpack(zipped("metadata104", b'{"@graph": []}'), "metadata104"),
         b'{"@graph": []}', "the one file a release's zip holds comes out as it went in")
    try:
        release.unpack(b"not a zip", "metadata104")
        s.check(False, "a broken archive raises")
    except ValueError:
        s.check(True, "a broken archive raises rather than installing nothing")

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        current = root / "current"
        s.eq(release.held(current), {}, "with nothing installed, nothing is held")
        s.eq(release.short(b"x", current, "metadata101"), None,
             "and a first release has nothing to fall short of")

        release.install(root, "1.2.20", "2026-09-18",
                        {"metadata101": b"a" * 100, "metadata104": b"b" * 50}, "2026-10-01")
        s.eq(release.held(current), {"tag": "1.2.20", "published": "2026-09-18",
                                     "retrieved": "2026-10-01"},
             "an installed release names its tag, when MADB published it and when it was read")
        s.eq((current / "metadata101.json").read_bytes(), b"a" * 100, "beside its files")

        # THE BIBLIOGRAPHY DOES NOT SHRINK. A file far smaller than the one held is a truncated
        # download or a broken export, and installing it would unlearn last month's books.
        s.check(release.short(b"a" * 60, current, "metadata101"),
                "a file under nine tenths of the held one is refused")
        s.eq(release.short(b"a" * 95, current, "metadata101"), None,
             "while one a little smaller, as a corrected record can make it, is not")

        release.install(root, "1.2.21", "2026-10-16",
                        {"metadata101": b"c" * 110, "metadata104": b"d" * 50}, "2026-11-01")
        s.eq(json.loads((current / "RELEASE.json").read_text())["tag"], "1.2.21",
             "a newer release takes the held one's place")
        s.eq(sorted(p.name for p in root.iterdir()), ["current"],
             "and leaves nothing of the old one or of the swap behind")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "madb.release"))
