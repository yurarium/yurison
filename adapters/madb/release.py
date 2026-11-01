#!/usr/bin/env python3
"""The national bibliography's newest release, kept in the cache where every MADB route reads it.

WHY THIS EXISTS. Every MADB route reads a release directory somebody downloaded by hand, and that
was done once, on 2026-08-01, at release 1.2.18. The Media Arts Database publishes a release a
month on GitHub, so by November the routes were three releases behind, and a book printed since
July was one the bibliography held and the corpus could not ask about. The routes were frozen for
that reason (docs/LAUNCH-PLAN.md section 2): their input was a hand act nobody would repeat.

WHAT IT KEEPS. `<root>/current/`, holding the two bulk files the routes read, `metadata101.json`
(単行本) and `metadata104.json` (series), and `RELEASE.json` naming the tag, when MADB published
it and when it was downloaded. The routes take `--cache <root>/current` and read the tag from
there, so a re-pin is this script running and nothing else. A release already held costs one
request to the GitHub API.

THE FLOOR. A new release replaces the held one only when each file arrived whole and is no smaller
than nine tenths of the file it replaces. The bibliography does not shrink: a release that reads
smaller is a truncated download or a broken export, and installing it would teach every route
that books it held last month do not exist. The held release stays and the run says why.

Usage:  release.py [--root $YURI_CACHE/madb-cache]
"""
import datetime
import io
import json
import pathlib
import shutil
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

LATEST = "https://api.github.com/repos/mediaarts-db/dataset/releases/latest"
#: The bulk files the routes read: 単行本 and the series they belong to.
WANT = ("metadata101", "metadata104")
#: How much of the held file a new one must reach. See THE FLOOR above.
FLOOR = 0.9


def latest(doc):
    """`(tag, published, {name: asset url})` out of GitHub's answer for the latest release."""
    assets = {a["name"]: a["browser_download_url"] for a in doc.get("assets") or []}
    urls = {n: assets.get(f"{n}_json.zip") for n in WANT}
    return doc.get("tag_name"), (doc.get("published_at") or "")[:10], urls


def held(directory):
    """What `RELEASE.json` in a release directory says, or {} where there is none."""
    p = pathlib.Path(directory) / "RELEASE.json"
    return json.loads(p.read_text()) if p.exists() else {}


def unpack(blob, name):
    """The one JSON file a release's zip holds, as bytes. Raises ValueError on a broken archive."""
    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
        if z.testzip() is not None:
            raise ValueError(f"{name}_json.zip fails its own checksum")
        return z.read(f"{name}.json")
    except (zipfile.BadZipFile, KeyError) as e:
        raise ValueError(f"{name}_json.zip: {e}") from None


def short(new, current, name):
    """Why a new file may not replace the held one, or None where it may."""
    p = pathlib.Path(current) / f"{name}.json"
    if p.exists() and len(new) < FLOOR * p.stat().st_size:
        return (f"{name}.json is {len(new):,} bytes against {p.stat().st_size:,} held, "
                f"under {FLOOR:.0%}")
    return None


def install(root, tag, published, files, today):
    """Write the release beside the held one and swap it in, so a failure leaves the held one."""
    root = pathlib.Path(root)
    new, current, old = root / "current.new", root / "current", root / "current.old"
    shutil.rmtree(new, ignore_errors=True)
    new.mkdir(parents=True)
    for name, data in files.items():
        (new / f"{name}.json").write_bytes(data)
    (new / "RELEASE.json").write_text(json.dumps(
        {"tag": tag, "published": published, "retrieved": today}, indent=2) + "\n")
    shutil.rmtree(old, ignore_errors=True)
    if current.exists():
        current.rename(old)
    new.rename(current)
    shutil.rmtree(old, ignore_errors=True)


def main(argv=None):
    import argparse

    import net
    import paths

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(paths.cache("madb-cache")))
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root)
    current = root / "current"
    today = datetime.date.today().isoformat()

    try:
        doc = json.loads(net.body(net.fetch(LATEST, None)) or "{}")
    except net.Refused as e:
        print(f"HEALTH: GitHub refused the release listing: {e}. The held release stays.")
        return 1
    tag, published, urls = latest(doc)
    have = held(current).get("tag")
    if not tag or not all(urls.values()):
        print(f"HEALTH: the latest release lists no {', '.join(WANT)} JSON assets. "
              "Refusing to write.")
        return 1
    if tag == have:
        print(f"madb: release {tag} is held; nothing to fetch")
        return 0

    files = {}
    for name, url in urls.items():
        r = net.fetch(url, None, binary=True)
        if r.raw is None:
            print(f"HEALTH: {name}_json.zip did not arrive ({r.error or r.status}). "
                  f"Refusing to write; release {have or 'none'} stays.")
            return 1
        try:
            data = unpack(r.raw, name)
        except ValueError as e:
            print(f"HEALTH: {e}. Refusing to write; release {have or 'none'} stays.")
            return 1
        why = short(data, current, name)
        if why:
            print(f"HEALTH: {why}. The bibliography does not shrink, so this is a broken "
                  f"release. Refusing to write; release {have} stays.")
            return 1
        files[name] = data
    install(root, tag, published, files, today)
    print(f"madb: release {tag} (published {published}) installed in place of {have or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
