#!/usr/bin/env python3
"""Which hosts the update run reaches through our server in Tokyo, and the lines that set it up.

WHY THIS EXISTS. From 2026-10-22 every comici site has answered 403 with a page reading
「現在、一部の通信環境からのアクセスを制限しております」: access restricted by network. From a server in
Tokyo the same pages answer. The owner ruled on 2026-11-05 that reading them from a network the
site allows, through a server we hold, is ordinary use (REQUIREMENTS, "Where the platform has closed
to us"). Nothing else about the request changes. The user agent, robots.txt and the pause per host
are the same ones every other fetch keeps, and a refusal through the server is still a refusal.

HOW, AND WHY BELOW PYTHON. Thirty-odd modules open URLs, each with its own urlopen, and two drive
Chromium. Teaching each of them a proxy would leave the next one written without it. So the update
workflow opens one SSH connection to the server with a local forward per host, each on its own
loopback address at port 443, and then points the host's name at that address in /etc/hosts. The
server makes the connection to the site, TLS runs end to end with the site's own certificate, and
every client takes the route without being told. A host this file does not name is fetched
directly, as before.

WHAT HAPPENS WHEN IT FAILS. The workflow writes /etc/hosts only once the forwards are up and a
request through them has answered. A connection that drops mid-run makes those fetches fail below
HTTP, and platform_access records nothing for a run like that, so the platform stays closed and the
listing sites' reports go on publishing. The route can only ever add reads.

The key the workflow holds is restricted on the server to exactly these forwards (`permitopen`): it
opens no shell and reaches no other host.

Usage:  route.py forwards | hosts-file | authorized-keys | probe
"""
import argparse
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITES = ROOT / "adapters" / "webpages" / "sites.yaml"

#: The value of a site's `route` key that sends it through the server in Tokyo.
JP = "jp"

#: Linux answers on the whole of 127/8, so each host gets an address of its own and every forward
#: can listen on the port its URLs name.
BASE = "127.0.1."
PORT = 443


def hosts(sites):
    """The hosts to route, from the webpages registry's rows marked `route: jp`."""
    return sorted({s["host"] for s in sites if s.get("route") == JP})


def plan(names):
    """Each host paired with the loopback address its forward listens on."""
    names = sorted(set(names))
    if len(names) > 254:
        raise ValueError(f"{len(names)} hosts will not fit in {BASE}0/24")
    return [(h, f"{BASE}{i}") for i, h in enumerate(names, 1)]


def forwards(pairs):
    """The `ssh -L` arguments, one per host: listen here, connect from the server."""
    out = []
    for host, addr in pairs:
        out += ["-L", f"{addr}:{PORT}:{host}:{PORT}"]
    return out


def hosts_file(pairs):
    """The /etc/hosts lines that send each name to its forward."""
    return [f"{addr} {host}" for host, addr in pairs]


def authorized_keys(pairs):
    """The options to put before the workflow's key in the server's authorized_keys.

    `restrict` takes away everything, `port-forwarding` gives back local forwards, `permitopen`
    limits those to these hosts, and the forced command means a session gets no shell.
    """
    opens = ",".join(f'permitopen="{h}:{PORT}"' for h, _a in pairs)
    return f'restrict,port-forwarding,command="/usr/sbin/nologin",{opens}'


def probe(pairs):
    """One page to ask through the route before trusting it: the first host's front page.

    NOT ITS robots.txt, which these sites serve to every network. A 200 for that would come back
    with the route broken, so it proves nothing. The front page is refused unless the route works.
    """
    return f"https://{pairs[0][0]}/" if pairs else ""


def load(path=SITES):
    return (yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8")) or {}).get("sites") or []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", choices=("forwards", "hosts-file", "authorized-keys", "probe"))
    ap.add_argument("--sites", default=str(SITES))
    a = ap.parse_args(argv)
    pairs = plan(hosts(load(a.sites)))
    if not pairs:
        sys.exit(f"no site in {a.sites} is marked route: {JP}")
    if a.what == "forwards":
        print(" ".join(forwards(pairs)))
    elif a.what == "hosts-file":
        print("\n".join(hosts_file(pairs)))
    elif a.what == "authorized-keys":
        print(authorized_keys(pairs))
    else:
        print(probe(pairs))


if __name__ == "__main__":
    main()
