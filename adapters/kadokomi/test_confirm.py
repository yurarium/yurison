#!/usr/bin/env python3
"""kadokomi/confirm.py: the tags that make a work presumptively in scope.

COVERS = ['adapters/kadokomi/confirm.py']
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import confirm as kc


def main(s):
    # The tag vocabulary is the publisher's own, and all three name the same category. Dropping any
    # one silently narrows what the platform is understood to have said.
    s.check("百合" in kc.YURI_TAGS, "the Japanese term is recognised")
    s.check("GL" in kc.YURI_TAGS, "the GL abbreviation is recognised")
    s.check("ガールズラブ" in kc.YURI_TAGS, "the katakana form is recognised")

    # RATING SEMANTICS ARE NOT KNOWN, and the flag says so. This matters because REQUIREMENTS
    # excludes works marketed as pornography, and acting on a rating field whose meaning has not
    # been established would be inventing an exclusion rule from a number.
    s.check(kc.RATING_SEMANTICS_KNOWN is False,
            "the rating field's meaning is recorded as unestablished, not assumed")

    payload = {"work": {"title": "百合の花", "tags": [{"name": "百合"}]}}
    page = ('<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": {"dehydratedState": {"queries": [
                {"state": {"data": payload}}]}}}})
            + "</script>")
    s.check(kc.work_data(page) is not None, "the embedded work block is found")
    s.check(kc.work_data("<html>nothing</html>") is None,
            "a page without the block yields None rather than raising")
    s.check(kc.work_data('<script id="__NEXT_DATA__">not json</script>') is None,
            "malformed JSON yields None rather than taking the run down")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "kadokomi.confirm"))
