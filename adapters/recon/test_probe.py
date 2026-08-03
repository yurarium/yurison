#!/usr/bin/env python3
"""recon/probe.py: robots rules, and what counts as a feed.

COVERS = ['adapters/recon/probe.py']

Reconnaissance decides where this project may look at all, so the robots parsing is a courtesy
constraint rather than a convenience. Reading it too loosely means fetching what a host asked us
not to.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import probe


def main(s):
    # A 200 is not a feed. Several sites answer every unknown path with their homepage, so trusting
    # the status would register a feed at every host that has none.
    s.check(probe.is_feed("application/xml", ""), "an xml content type is a feed")
    s.check(probe.is_feed("application/rss+xml", ""), "rss in the content type is a feed")
    s.check(probe.is_feed("text/html", '<?xml version="1.0"?><feed>'),
            "an xml body is a feed even when the type says html")
    s.check(probe.is_feed("text/html", "  <rss version='2.0'>"),
            "leading whitespace does not hide an rss body")
    s.check(not probe.is_feed("text/html", "<!doctype html><html>"),
            "a homepage returned with 200 is not a feed")
    s.check(not probe.is_feed(None, None), "nothing is not a feed, and does not raise")

    # Disallow rules. A prefix match, with "/" ignored because a blanket disallow would otherwise
    # exclude every host that publishes one.
    dis = ["/private", "/tmp*"]
    s.check(probe.allowed("/series/1", dis), "an unlisted path is allowed")
    s.check(not probe.allowed("/private/x", dis), "a disallowed prefix is refused")
    s.check(not probe.allowed("/tmp/x", dis), "a trailing wildcard is stripped before matching")
    s.check(probe.allowed("/anything", []), "no rules means allowed")
    s.check(probe.allowed("/anything", ["/"]),
            "a blanket / is ignored, or every host publishing one would be excluded")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "recon.probe"))
