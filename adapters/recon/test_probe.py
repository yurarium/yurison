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

    # NDL SEARCH, QUOTED FROM https://ndlsearch.ndl.go.jp/robots.txt AS SERVED 2026-08-05, cut to
    # the shape that mattered: a long list of rules with the one that governs the API near the end.
    # The parser cut the list to twelve, so `/api` fell off it and three rounds of author lookups
    # went out on a path this file forbids. The counter-case is the point of the test: the twelfth
    # rule was always found, and the twenty-ninth never was.
    NDL = ("User-agent: *\n\n"
           "Disallow: /account\nDisallow: /emailchg\nDisallow: /ksp\nDisallow: /error\n"
           "Disallow: /favorite\nDisallow: /ill_request/\nDisallow: /inputpassword\n"
           "Disallow: /openurl\nDisallow: /register/\nDisallow: /request\n"
           "Disallow: /resetpassword/complete\nDisallow: /settings/library\nDisallow: /user\n"
           "Disallow: /search/history\nDisallow: /en/account\nDisallow: /en/emailchg\n"
           "Disallow: /en/ksp\nDisallow: /en/error\nDisallow: /en/favorite\n"
           "Disallow: /en/ill_request/\nDisallow: /en/inputpassword\nDisallow: /en/openurl\n"
           "Disallow: /en/register/\nDisallow: /en/request\nDisallow: /en/resetpassword/complete\n"
           "Disallow: /en/settings/library\nDisallow: /en/user\nDisallow: /en/search/history\n"
           "Disallow: /api\nDisallow: /statistics\n\n"
           "Sitemap: https://ndlsearch.ndl.go.jp/sitemap.xml\n")
    rules = probe.disallow_rules(NDL)
    s.eq(len(rules), 30, "every rule for * is kept, not the first handful")
    s.check(not probe.allowed("/api/opensearch", rules),
            "the creator lookup is on a path robots refuses")
    s.check(not probe.allowed("/account", rules), "and the first rule still refuses its path")
    s.check(probe.allowed("/search", rules), "while a path no rule names stays open")

    # A blank line between the user-agent line and its rules does not start a new group. NDL's file
    # has one, and reading it as a separator would leave every rule below it unattached and the
    # whole host permitted.
    s.check(not probe.allowed("/api", probe.disallow_rules("User-agent: *\n\nDisallow: /api\n")),
            "a blank line after the user-agent does not end the group")
    # Rules under another crawler's name are not ours to obey or to inherit.
    s.eq(probe.disallow_rules("User-agent: Googlebot\nDisallow: /x\n"), [],
         "a rule addressed to another crawler is not a rule for us")
    s.eq(probe.disallow_rules(""), [], "an empty file forbids nothing, and does not raise")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "recon.probe"))
