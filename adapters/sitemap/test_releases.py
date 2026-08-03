#!/usr/bin/env python3
"""sitemap/releases.py: reading a sitemap, and the entity-decoding bug behind chapter titles.

COVERS = ['adapters/sitemap/releases.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as sm

SITEMAP = """<urlset>
  <url><loc>https://x.jp/episode/1</loc><lastmod>2026-08-01</lastmod></url>
  <url><loc>https://x.jp/episode/2</loc><lastmod>2026-08-08T12:00:00+09:00</lastmod></url>
  <url><loc>https://x.jp/no-date</loc></url>
  <url><lastmod>2026-08-15</lastmod></url>
</urlset>"""


def main(s):
    got = sm.entries(SITEMAP)
    s.eq(len(got), 2, "only entries with BOTH a location and a date are usable")
    s.eq(got[0], ("https://x.jp/episode/1", "2026-08-01"), "url and date are paired")
    s.eq(got[1][1], "2026-08-08", "a timestamped lastmod is trimmed to its date")
    s.eq(sm.entries("<urlset></urlset>"), [], "an empty sitemap yields nothing")
    s.eq(sm.entries("not xml at all"), [], "junk yields nothing rather than raising")

    # THE ENTITY BUG. マガポケ writes the separating slash as &#x2F;, so splitting the raw title
    # matched nothing and the platform name stayed welded to the chapter. The row still had a
    # chapter, an author and a date, so every field check passed and it shipped. Decoding must
    # happen BEFORE the split, which is what this pins.
    title = "作品 | 【第1話】ぐっすん！ &#x2F; マガポケ | 講談社"

    def fake_get(url, _t=title):
        return f"<html><title>{_t}</title></html>"

    real, sm.get = sm.get, fake_get
    try:
        s.eq(sm.chapter_title("https://x.jp/e/1"), "【第1話】ぐっすん！",
             "the encoded slash is decoded before splitting, so the platform name is removed")

        sm.get = lambda u: "<html><title>only one part</title></html>"
        s.check(sm.chapter_title("u") is None, "a title that does not fit the shape yields None")

        sm.get = lambda u: "<html>no title element</html>"
        s.check(sm.chapter_title("u") is None, "a page without a title yields None")

        sm.get = lambda u: None
        s.check(sm.chapter_title("u") is None, "a failed fetch yields None rather than raising")
    finally:
        sm.get = real


if __name__ == "__main__":
    sys.exit(testkit.run(main, "sitemap.releases"))
