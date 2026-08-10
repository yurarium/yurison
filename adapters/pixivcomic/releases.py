#!/usr/bin/env python3
"""pixivコミック adapter.

Reads a candidate list, fetches series detail + episode list for each named work,
and writes data/source/pixivcomic/works.yaml.

Candidate-named works only; no catalogue crawling. Records are written as fetched;
corrections belong in data/overlay/.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from facts import marketing as _marketing                               # noqa: E402

SITE = "https://comic.pixiv.net"
API_ROOT = f"{SITE}/api/app"

# Client-identity marker this API is fed; keep it even if the others are trimmed.
CLIENT_MARKER = "pixivcomic"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
)

# Platform-stated dates are shown in Japan time; convert epoch ms against that offset
# so the emitted date matches what the platform displays.
PLATFORM_TZ = timezone(timedelta(hours=9))

MIN_WORKS = 5
# ASKED OF `facts/marketing`, which owns it. This vocabulary decides what the database
# admits and it had three homes until 2026-08-10.
YURI_TAGS = _marketing.TAGS
REQUEST_TIMEOUT = 30
WORK_URL_RE = re.compile(r"comic\.pixiv\.net/works/(\d+)")

# Directories this adapter must never write into (§1: source tree only).
FORBIDDEN_OUT_PARTS = {"build", "overlay", "queue"}

# Failure categories, reported and counted separately (§8).
NOT_JSON = "response not JSON (interstitial / maintenance page)"
BAD_SHAPE = "JSON did not match expected shape"
NOT_FOUND = "work id 404 (withdrawn or moved)"
HTTP_ERROR = "non-success status or transport error"
NO_EPISODES = "no usable episodes (all wrappers null)"
FAILURE_ORDER = [NOT_JSON, BAD_SHAPE, NOT_FOUND, HTTP_ERROR, NO_EPISODES]


class Failure(Exception):
    """A per-work failure. Never aborts the run; counted by category."""

    def __init__(self, category: str, detail: str) -> None:
        super().__init__(detail)
        self.category = category
        self.detail = detail


@dataclass
class Report:
    requested: int = 0
    resolved: int = 0
    failures: dict[str, list[str]] = field(default_factory=dict)
    dropped_chapters: int = 0
    suspicious_dates: int = 0

    def fail(self, category: str, series_id: int, detail: str) -> None:
        self.failures.setdefault(category, []).append(f"{series_id}: {detail}")

    @property
    def failed(self) -> int:
        return sum(len(v) for v in self.failures.values())


class Throttle:
    """~1s pause between network requests; cache hits do not count as requests."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self._last = 0.0

    def wait(self) -> None:
        if self.seconds <= 0:
            return
        elapsed = time.monotonic() - self._last
        if self._last and elapsed < self.seconds:
            time.sleep(self.seconds - elapsed)
        self._last = time.monotonic()


# --- candidate list ---------------------------------------------------------


def _walk_strings(node: Any) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str):
                yield key
            yield from _walk_strings(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk_strings(item)


def load_candidate_ids(path: Path) -> list[int]:
    """Series ids taken from comic.pixiv.net/works/<id> URLs in the candidate list.

    The candidate file's exact layout is not assumed: every string in the document is
    scanned, with a raw-text scan as fallback when the structured walk finds nothing.
    """
    text = path.read_text(encoding="utf-8")

    haystack: list[str] = [text]
    try:
        import yaml  # type: ignore

        parsed = list(_walk_strings(yaml.safe_load(text)))
        if any(WORK_URL_RE.search(s) for s in parsed):
            haystack = parsed
    except ImportError:
        pass
    except Exception as exc:  # malformed YAML: fall back to the raw scan
        print(f"warning: could not parse {path} as YAML ({exc}); scanning raw text", file=sys.stderr)

    ids: list[int] = []
    seen: set[int] = set()
    for chunk in haystack:
        for match in WORK_URL_RE.finditer(chunk):
            series_id = int(match.group(1))
            if series_id not in seen:
                seen.add(series_id)
                ids.append(series_id)
    return ids


# --- transport --------------------------------------------------------------


def http_get(url: str, user_agent: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "X-Requested-With": CLIENT_MARKER,
            "Referer": f"{SITE}/",
            "Origin": SITE,
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        category = NOT_FOUND if exc.code == 404 else HTTP_ERROR
        raise Failure(category, f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise Failure(HTTP_ERROR, f"transport error for {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise Failure(HTTP_ERROR, f"timeout for {url}") from exc


def fetch_json(url: str, cache_file: Path | None, user_agent: str, throttle: Throttle) -> Any:
    if cache_file is not None and cache_file.exists():
        raw = cache_file.read_text(encoding="utf-8")
    else:
        throttle.wait()
        raw = http_get(url, user_agent)
        if cache_file is not None:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(raw, encoding="utf-8")
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise Failure(NOT_JSON, f"{url}: {exc}") from exc


# --- mapping ----------------------------------------------------------------


def require_mapping(node: Any, key: str, where: str) -> dict:
    if not isinstance(node, dict):
        raise Failure(BAD_SHAPE, f"{where}: expected an object")
    value = node.get(key)
    if not isinstance(value, dict):
        raise Failure(BAD_SHAPE, f"{where}: missing object '{key}'")
    return value


def clean_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def extract_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    for entry in value:
        name = clean_str(entry.get("name")) if isinstance(entry, dict) else None
        if name:
            name = name.lstrip("#").strip()
        if name and name not in tags:
            tags.append(name)
    return tags


def epoch_ms_to_date(value: Any, report: Report) -> str | None:
    """Epoch milliseconds to YYYY-MM-DD. Null, absent or non-positive omits the date."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value <= 0:
        return None
    try:
        stamp = datetime.fromtimestamp(value / 1000, PLATFORM_TZ)
    except (OverflowError, OSError, ValueError):
        report.suspicious_dates += 1
        return None
    if not 2000 <= stamp.year <= date.today().year + 2:
        # Wrong unit would land every date here; surfaced rather than silently emitted.
        report.suspicious_dates += 1
    return stamp.strftime("%Y-%m-%d")


def map_chapters(episodes_json: Any, report: Report) -> list[dict]:
    data = require_mapping(episodes_json, "data", "episode list")
    wrappers = data.get("episodes")
    if not isinstance(wrappers, list):
        raise Failure(BAD_SHAPE, "episode list: 'episodes' is not an array")

    chapters: list[dict] = []
    for wrapper in wrappers:
        if not isinstance(wrapper, dict):
            continue
        episode = wrapper.get("episode")
        if not isinstance(episode, dict):  # null wrappers are dropped before mapping
            continue

        episode_id = episode.get("id")
        title = clean_str(episode.get("numbering_title"))
        if isinstance(episode_id, bool) or not isinstance(episode_id, int) or not title:
            report.dropped_chapters += 1
            continue

        chapter: dict[str, Any] = {"title": title}
        subtitle = clean_str(episode.get("sub_title"))
        if subtitle:
            chapter["subtitle"] = subtitle
        updated = epoch_ms_to_date(episode.get("read_start_at"), report)
        if updated:
            chapter["updated"] = updated
        chapter["episode_id"] = episode_id
        chapter["access_modes"] = ["free" if episode.get("state") == "readable" else "purchase"]
        chapters.append(chapter)

    if not chapters:
        raise Failure(NO_EPISODES, "every episode wrapper was null or unusable")

    # Fetched newest-first; emitted oldest-first without re-sorting, so platform order
    # is preserved even where dates are missing.
    chapters.reverse()
    return chapters


def parse_official_work(series_id: int, detail_json: Any) -> dict:
    """Validates the detail response before an episode request is spent on the work."""
    data = require_mapping(detail_json, "data", f"work {series_id}")
    official = require_mapping(data, "official_work", f"work {series_id}")
    if not clean_str(official.get("name")):
        raise Failure(BAD_SHAPE, "work name absent")
    return official


def build_work(series_id: int, official: dict, episodes_json: Any, retrieved: str, report: Report) -> dict:
    title = clean_str(official.get("name"))
    if not title:
        raise Failure(BAD_SHAPE, "work name absent")

    url = f"{SITE}/works/{series_id}"
    work: dict[str, Any] = {"work_title": title}

    author = clean_str(official.get("author"))
    if author:
        work["author"] = author

    work["series_id"] = series_id
    work["url"] = url

    tags = extract_tags(official.get("tags"))
    if tags:
        work["tags"] = tags

    matched = next((tag for tag in tags if tag in YURI_TAGS), None)
    if matched:
        work["marketing_label"] = "yuri"
        work["marketing_label_basis"] = {
            "source": "pixivcomic",
            "url": url,
            "retrieved": retrieved,
            "note": f"Publisher applies the tag {matched} on pixivコミック.",
        }

    chapters = map_chapters(episodes_json, report)
    work["chapter_count"] = len(chapters)
    work["chapters"] = chapters
    return work


def resolve_work(
    series_id: int,
    cache_dir: Path | None,
    user_agent: str,
    throttle: Throttle,
    retrieved: str,
    report: Report,
) -> dict:
    detail_cache = cache_dir / f"works-v5-{series_id}.json" if cache_dir else None
    episodes_cache = cache_dir / f"episodes-v2-{series_id}.json" if cache_dir else None

    detail = fetch_json(f"{API_ROOT}/works/v5/{series_id}", detail_cache, user_agent, throttle)
    official = parse_official_work(series_id, detail)
    episodes = fetch_json(
        f"{API_ROOT}/works/{series_id}/episodes/v2?order=desc",
        episodes_cache,
        user_agent,
        throttle,
    )
    return build_work(series_id, official, episodes, retrieved, report)


# --- output -----------------------------------------------------------------

_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def dq(value: str) -> str:
    out = []
    for char in value:
        if char in _ESCAPES:
            out.append(_ESCAPES[char])
        elif ord(char) < 0x20:
            out.append(f"\\x{ord(char):02x}")
        else:
            out.append(char)
    return '"' + "".join(out) + '"'


def inline_list(values: list[str]) -> str:
    return "[" + ", ".join(dq(v) for v in values) + "]"


def render_yaml(works: list[dict], retrieved: str) -> str:
    lines = [
        "source: pixivcomic",
        "platform: pixivcomic",
        "platform_name: pixivコミック",
        "publisher: ピクシブ",
        f"retrieved: {retrieved}",
        "record_type: web_work_chapters",
        "identification_mode: discovery-candidate",
        "date_basis: platform-stated",
        "date_confidence: reported",
        f"works_resolved: {len(works)}",
        "works:",
    ]

    for work in works:
        lines.append(f"  - work_title: {dq(work['work_title'])}")
        if "author" in work:
            lines.append(f"    author: {dq(work['author'])}")
        lines.append(f"    series_id: {work['series_id']}")
        lines.append(f"    url: {dq(work['url'])}")
        if "tags" in work:
            lines.append(f"    tags: {inline_list(work['tags'])}")
        if "marketing_label" in work:
            basis = work["marketing_label_basis"]
            lines.append(f"    marketing_label: {work['marketing_label']}")
            lines.append("    marketing_label_basis:")
            lines.append(f"      source: {basis['source']}")
            lines.append(f"      url: {dq(basis['url'])}")
            lines.append(f"      retrieved: {basis['retrieved']}")
            lines.append(f"      note: {dq(basis['note'])}")
        lines.append(f"    chapter_count: {work['chapter_count']}")
        lines.append("    chapters:")
        for chapter in work["chapters"]:
            lines.append(f"      - title: {dq(chapter['title'])}")
            if "subtitle" in chapter:
                lines.append(f"        subtitle: {dq(chapter['subtitle'])}")
            if "updated" in chapter:
                lines.append(f"        updated: {chapter['updated']}")
            lines.append(f"        episode_id: {chapter['episode_id']}")
            lines.append(f"        access_modes: {inline_list(chapter['access_modes'])}")

    return "\n".join(lines) + "\n"


def check_out_dir(out_dir: Path) -> None:
    parts = {part.lower() for part in out_dir.resolve().parts}
    clashes = parts & FORBIDDEN_OUT_PARTS
    if clashes:
        raise SystemExit(
            f"refusing to write into {out_dir}: adapters write to the source tree only "
            f"(path contains {', '.join(sorted(clashes))})"
        )


def health_checks(works: list[dict], report: Report) -> list[str]:
    problems = []
    if len(works) < MIN_WORKS:
        problems.append(f"only {len(works)} works resolved, minimum is {MIN_WORKS}")
    total_chapters = sum(work["chapter_count"] for work in works)
    if total_chapters == 0:
        problems.append("zero chapters across all works")
    dated = sum(1 for work in works for chapter in work["chapters"] if "updated" in chapter)
    if dated == 0:
        problems.append("no chapter carries a date")
    if report.requested and report.failed * 2 > report.requested:
        problems.append(f"{report.failed} of {report.requested} requested works failed")
    return problems


def write_report(report: Report, works: list[dict]) -> None:
    total_chapters = sum(work["chapter_count"] for work in works)
    dated = sum(1 for work in works for chapter in work["chapters"] if "updated" in chapter)
    free = sum(
        1
        for work in works
        for chapter in work["chapters"]
        if chapter["access_modes"] == ["free"]
    )
    print(
        f"requested {report.requested}, resolved {report.resolved}, failed {report.failed}",
        file=sys.stderr,
    )
    print(
        f"chapters {total_chapters} ({dated} dated, {free} free, {total_chapters - free} purchase)",
        file=sys.stderr,
    )
    for category in FAILURE_ORDER:
        entries = report.failures.get(category)
        if entries:
            print(f"  {category}: {len(entries)}", file=sys.stderr)
            for entry in entries:
                print(f"    - {entry}", file=sys.stderr)
    if report.dropped_chapters:
        print(f"  episodes dropped (no id or numbering_title): {report.dropped_chapters}", file=sys.stderr)
    if report.suspicious_dates:
        print(
            f"  implausible dates: {report.suspicious_dates} — confirm read_start_at is "
            "epoch milliseconds against a known date",
            file=sys.stderr,
        )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pixivコミック adapter")
    parser.add_argument("--works", required=True, type=Path, help="candidate list (claim-targets shape)")
    parser.add_argument("--out", required=True, type=Path, help="output directory, e.g. data/source/pixivcomic")
    parser.add_argument("--cache", type=Path, help="directory for raw responses (not committed)")
    parser.add_argument(
        "--retrieved",
        default=date.today().isoformat(),
        help="YYYY-MM-DD retrieval date (default: today)",
    )
    parser.add_argument("--sleep", type=float, default=1.0, help="pause between requests, seconds")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        # strptime tolerates unpadded input, so re-emit rather than trusting the argument.
        retrieved = datetime.strptime(args.retrieved, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise SystemExit(f"--retrieved must be YYYY-MM-DD, got {args.retrieved!r}")

    check_out_dir(args.out)

    if not args.works.is_file():
        raise SystemExit(f"candidate list not found: {args.works}")

    series_ids = load_candidate_ids(args.works)
    if not series_ids:
        raise SystemExit(f"no comic.pixiv.net/works/<id> URLs found in {args.works}")

    if args.cache:
        args.cache.mkdir(parents=True, exist_ok=True)

    report = Report(requested=len(series_ids))
    throttle = Throttle(args.sleep)
    works: list[dict] = []

    for series_id in series_ids:
        try:
            works.append(resolve_work(series_id, args.cache, args.user_agent, throttle, retrieved, report))
            report.resolved += 1
        except Failure as failure:
            report.fail(failure.category, series_id, failure.detail)

    write_report(report, works)

    problems = health_checks(works, report)
    if problems:
        print("health checks failed, nothing written:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / "works.yaml"
    tmp = target.with_suffix(".yaml.tmp")
    tmp.write_text(render_yaml(works, retrieved), encoding="utf-8")
    tmp.replace(target)
    print(f"wrote {target} ({len(works)} works)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
