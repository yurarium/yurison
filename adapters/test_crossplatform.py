#!/usr/bin/env python3
"""Tests for cross-platform release merging (REQUIREMENTS §5).

Built against no real multi-platform data — only 一迅プラス is producing releases so far — so the
behaviour is pinned by test rather than by observation. Every case here is a stated fact about how
Japanese web-manga platforms behave.

Run: python3 adapters/test_crossplatform.py
"""
import sys

from crossplatform import carriage, episode_key, merge_releases

RANKS = {"カドコミ": 1, "COMIC FUZ": 1, "ニコニコ漫画": 3, "pixivコミック": 3, "サンデーうぇぶり": None}
FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    if not ok:
        print(f"        got  {got!r}\n        want {want!r}")
        FAILS.append(name)


print("episode keys match across platform numbering conventions")
check("第7話 == 7話", episode_key("第7話"), episode_key("7話"))
check("第7話 == #7", episode_key("第7話"), episode_key("#7"))
check("full-width digits", episode_key("第７話"), episode_key("第7話"))
check("chapter 7 != chapter 8", episode_key("第7話") != episode_key("第8話"), True)
check("titled episodes fall back to the title",
      episode_key("スズラン手帖") == episode_key("スズラン手帖"), True)

print("\nsame chapter on two platforms is one release")
rows = [
    {"work": "A", "episode": "第7話", "platform": "カドコミ", "date": "2026-07-01", "url": "u1"},
    {"work": "A", "episode": "7話", "platform": "ニコニコ漫画", "date": "2026-07-01", "url": "u2"},
]
m = merge_releases(rows, RANKS)
check("merged to one entry", len(m), 1)
check("points at the better platform", m[0]["preferred"], "カドコミ")
check("names the alternative", m[0]["also_on"], ["ニコニコ漫画"])

print("\nreleases a day or two apart still merge")
rows = [
    {"work": "A", "episode": "第7話", "platform": "ニコニコ漫画", "date": "2026-07-03", "url": "u2"},
    {"work": "A", "episode": "第7話", "platform": "カドコミ", "date": "2026-07-01", "url": "u1"},
]
m = merge_releases(rows, RANKS)
check("still one entry", len(m), 1)
check("date is the earliest sighting", m[0]["date"], "2026-07-01")
check("preferred is still the better platform", m[0]["preferred"], "カドコミ")

print("\nfar apart is NOT merged — that is a different release")
rows = [
    {"work": "A", "episode": "第7話", "platform": "カドコミ", "date": "2026-07-01", "url": "u1"},
    {"work": "A", "episode": "第7話", "platform": "ニコニコ漫画", "date": "2026-09-20", "url": "u2"},
]
check("two entries", len(merge_releases(rows, RANKS)), 2)

print("\nwhen the better platform does not carry a chapter, point at one that does")
rows = [
    {"work": "A", "episode": "第12話", "platform": "カドコミ", "date": "2026-07-01", "url": "k12"},
    {"work": "A", "episode": "第12話", "platform": "ニコニコ漫画", "date": "2026-07-01", "url": "n12"},
    # カドコミ silently stopped; only ニコニコ has 13.
    {"work": "A", "episode": "第13話", "platform": "ニコニコ漫画", "date": "2026-07-08", "url": "n13"},
]
m = {e["episode"]: e for e in merge_releases(rows, RANKS)}
check("ch12 points at カドコミ", m["第12話"]["preferred"], "カドコミ")
check("ch13 points at ニコニコ漫画", m["第13話"]["preferred"], "ニコニコ漫画")
check("ch13 lists no alternative", m["第13話"]["also_on"], [])

print("\nunranked platforms lose to ranked ones but still win over nothing")
rows = [
    {"work": "B", "episode": "第1話", "platform": "サンデーうぇぶり", "date": "2026-07-01", "url": "s1"},
]
check("unranked used when sole source", merge_releases(rows, RANKS)[0]["preferred"], "サンデーうぇぶり")
rows.append({"work": "B", "episode": "第1話", "platform": "カドコミ", "date": "2026-07-01", "url": "k1"})
check("ranked beats unranked", merge_releases(rows, RANKS)[0]["preferred"], "カドコミ")

print("\nsilent carriage lapse is detected, not mistaken for the series ending")
rows = [
    {"work": "A", "episode": "第12話", "platform": "カドコミ", "date": "2026-07-01"},
    {"work": "A", "episode": "第15話", "platform": "ニコニコ漫画", "date": "2026-07-22"},
]
c = {r["platform"]: r for r in carriage(rows)}
check("lagging platform marked lapsed", c["カドコミ"]["status"], "lapsed")
check("leader stays active", c["ニコニコ漫画"]["status"], "active")
check("distance recorded", c["カドコミ"]["behind_by"], 3)

rows = [
    {"work": "A", "episode": "第15話", "platform": "カドコミ", "date": "2026-07-20"},
    {"work": "A", "episode": "第14話", "platform": "ニコニコ漫画", "date": "2026-07-15"},
]
c = {r["platform"]: r for r in carriage(rows)}
check("one chapter behind is not a lapse", c["ニコニコ漫画"]["status"], "active")

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: {', '.join(FAILS)}")
    sys.exit(1)
print("all cross-platform invariants hold")
