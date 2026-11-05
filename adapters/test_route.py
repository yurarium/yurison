#!/usr/bin/env python3
"""route.py: which hosts go through the server in Tokyo, and the lines the workflow sets up.

A host routed by mistake is fetched from another country for no reason, and the server's key would
refuse to forward it, so the fetch fails. A host missed is refused as before. The forwards, the
/etc/hosts lines and the key's permitopen list must all name the same hosts, or a name points at a
forward that does not exist.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import route


def main(s):
    sites = [{"host": "bigcomics.jp", "engine": "comici", "route": "jp"},
             {"host": "comic-days.com", "engine": "gigaviewer"},
             {"host": "takecomic.jp", "engine": "comici", "route": "jp"},
             {"host": "takecomic.jp", "engine": "comici", "route": "jp"},
             {"host": "example.jp", "route": "elsewhere"}]
    names = route.hosts(sites)
    s.eq(names, ["bigcomics.jp", "takecomic.jp"], "only rows marked route: jp, once each, sorted")

    pairs = route.plan(names)
    s.eq(pairs, [("bigcomics.jp", "127.0.1.1"), ("takecomic.jp", "127.0.1.2")],
         "each host gets its own loopback address, from .1")
    s.eq(len({a for _h, a in pairs}), len(pairs), "no two hosts share an address")

    s.eq(route.forwards(pairs),
         ["-L", "127.0.1.1:443:bigcomics.jp:443", "-L", "127.0.1.2:443:takecomic.jp:443"],
         "a forward listens on the host's address at 443 and connects to the host from the server")
    s.eq(route.hosts_file(pairs), ["127.0.1.1 bigcomics.jp", "127.0.1.2 takecomic.jp"],
         "each name points at its own forward")
    opts = route.authorized_keys(pairs)
    s.check(opts.startswith("restrict,port-forwarding,"), "the key gets forwarding and nothing else")
    s.check('command="/usr/sbin/nologin"' in opts, "a session on the key gets no shell")
    s.check('permitopen="bigcomics.jp:443"' in opts and 'permitopen="takecomic.jp:443"' in opts,
            "the key may open exactly the routed hosts")
    s.check("comic-days.com" not in opts, "and no host left unrouted")
    s.eq(route.probe(pairs), "https://bigcomics.jp/", "the probe asks a routed host's front page,"
         " which the block refuses, and not robots.txt, which it serves to everyone")
    s.eq(route.probe([]), "", "nothing routed, nothing to probe")

    s.raises(ValueError, lambda: route.plan([f"h{i}.jp" for i in range(255)]),
             "more hosts than the block holds is refused, not wrapped")

    # The real registry: every site marked is a comici site, the platforms that closed together.
    real = route.load()
    marked = [x for x in real if x.get("route") == route.JP]
    s.check(len(marked) > 0, "the registry marks some sites for the route")
    s.eq(sorted({x.get("engine") for x in marked}), ["comici"],
         "only comici sites are routed, the ones the 2026-11-05 ruling covers")

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "sites.yaml"
        p.write_text("sites:\n  - {host: a.jp, route: jp}\n", encoding="utf-8")
        s.eq(route.load(p), [{"host": "a.jp", "route": "jp"}], "a registry file loads its sites")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "route"))
