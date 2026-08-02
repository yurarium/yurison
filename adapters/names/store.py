#!/usr/bin/env python3
"""On-disk state for name resolution: what we know, what we tried, and how not to lose either.

NAMES-PLAN §4 makes self-checkpointing a requirement rather than a nicety, because this job runs
for days and WILL be interrupted. Three of its clauses shape everything here.

"STATE LIVES ON DISK, NOT IN A PROCESS", flushed as it goes. Taken literally that means rewriting a
YAML file after every single name, which is quadratic and would have the process spending its life
serialising. So there are two layers: an append-only journal that takes one fsync'd line per fact
the moment it is learned, and the YAML files that are compacted from it periodically. Killing the
process at any instant loses at most the name in flight — the journal has everything else, and
load() replays it over the YAML. The YAML is the reviewable artefact; the journal is the crash log
that makes the YAML safe to write lazily.

"RESOLVED IS FINAL" and "ATTEMPTS ARE RECORDED TOO". Both are the same mechanism: a pass asks the
store what is still open, and the store subtracts both the answered names and the names this pass
already asked about. Without the second half every restart re-pays for every miss, and §4a's
"closed, nothing to find" bucket never populates because nothing ever records having looked.

  An attempt is recorded ONLY when the source actually answered. A timeout, a 5xx, or a source
  being switched off (AniList is, right now — see pass2) is not evidence about a name and must
  never be written as one; doing so would permanently poison names the source could have resolved
  on a better day. This is the single easiest way to do lasting damage here, so the distinction is
  in the API: attempt() means "asked and told no", and transport failure aborts the pass instead.

ATTEMPTS LIVE IN THEIR OWN FILE. The alternative — an `attempted:` field on each record — was
tempting because it keeps one key in one place. Against it: attempts are per (name, pass, source)
and there are several per name, so they would dominate the file that a human actually reads when
checking readings; they churn on every run while resolved records are by definition final; and a
name can be attempted before any record exists for it, which would force empty carrier records into
authors.yaml purely as somewhere to hang bookkeeping. Separating them keeps authors.yaml and
titles.yaml as what they should be — the answers, diffable and reviewable — and puts the ledger
where its churn bothers nobody.

WHY MERGING NEEDS A RANK. §1: a stated preference must never be silently overwritten by a later
mechanical pass. So a new fact replaces an old one only if it outranks it; an equal-ranked
DIFFERENT value is a conflict and is kept alongside rather than resolved, because two sources
disagreeing about how a person's name is read is exactly the case where picking quietly is the
wrong move. An equal-ranked identical value is corroboration, which §1 says is worth paying for.
"""
import datetime
import json
import os
import pathlib
import tempfile

import yaml

KINDS = ("authors", "titles")

# How much a claim outranks another claim about the same field. Higher wins; equal-and-different is
# a conflict, never a silent overwrite.
EN_RANK = {
    # authors (§5): the person's own rendering beats anything we compute from a reading.
    "stated": 30,
    # titles (§5): the work's own English name beats our translation beats our romanisation.
    "official": 40,
    "translated": 20,
    "romaji": 10,
}

READING_RANK = {
    "surface": 50,        # the name is written in kana; the reading is not inferred, it is the name
    "stated": 40,         # a source gives kana explicitly (Wikidata P1814, MADB yomi, a furigana gloss)
    "aligned": 20,        # derived by aligning a whole-string reading against the surface (§5c)
    "back-converted": 10,  # recovered from a romanised string, lossy in the long vowels (§8.1)
    "guessed": 0,         # pass 4's business; never produced by passes 0-2
}


def today():
    return datetime.date.today().isoformat()


class NameStore:
    """authors.yaml + titles.yaml + attempts.yaml, with an append-only journal in front."""

    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.jdir = self.root / ".journal"
        self.records = {k: {} for k in KINDS}
        self.attempts = {}          # ja -> [ {pass, source, at} ]
        self._journals = {}
        self._dirty = 0
        self.load()

    # -- durability -----------------------------------------------------------------------------

    def _journal(self, name):
        if name not in self._journals:
            self.jdir.mkdir(parents=True, exist_ok=True)
            self._journals[name] = open(self.jdir / f"{name}.jsonl", "a", encoding="utf-8")
        return self._journals[name]

    def _append(self, name, entry):
        """One line, flushed and fsync'd. This is the durability guarantee; everything else is a
        cache of it."""
        f = self._journal(name)
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())

    def load(self):
        for kind in KINDS:
            path = self.root / f"{kind}.yaml"
            if path.exists():
                doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                self.records[kind] = doc.get("names") or {}
        apath = self.root / "attempts.yaml"
        if apath.exists():
            doc = yaml.safe_load(apath.read_text(encoding="utf-8")) or {}
            self.attempts = doc.get("attempts") or {}
        # The journal is replayed AFTER the YAML, because it is by construction the newer of the
        # two — it holds whatever was learned since the last compaction.
        for kind in KINDS:
            for entry in self._replay(kind):
                self._apply(kind, entry["ja"], entry["fact"])
        for entry in self._replay("attempts"):
            self._note_attempt(entry["ja"], entry["attempt"])

    def _replay(self, name):
        path = self.jdir / f"{name}.jsonl"
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # A half-written final line is the expected shape of a kill mid-write. It is the
                # name in flight, which §4 already accepts losing; everything before it is intact.
                continue

    def compact(self):
        """Write the YAML from memory, then drop the journal it superseded."""
        self.root.mkdir(parents=True, exist_ok=True)
        for kind in KINDS:
            self._write_yaml(self.root / f"{kind}.yaml", {
                "source": "overlay",
                "role": f"name-readings/{kind}",
                "note": HEADER_NOTE,
                "generated": today(),
                "names": self.records[kind],
            })
        self._write_yaml(self.root / "attempts.yaml", {
            "source": "overlay",
            "role": "name-resolution-attempts",
            "note": ATTEMPTS_NOTE,
            "generated": today(),
            "attempts": self.attempts,
        })
        for name in list(self._journals):
            self._journals.pop(name).close()
        for name in KINDS + ("attempts",):
            p = self.jdir / f"{name}.jsonl"
            if p.exists():
                p.unlink()
        self._dirty = 0

    def _write_yaml(self, path, doc):
        """Atomic: a crash during compaction must not be able to truncate the answers."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".yaml")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=True,
                               default_flow_style=False, width=100)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            pathlib.Path(tmp).unlink(missing_ok=True)
            raise

    def maybe_compact(self, every=200):
        if self._dirty >= every:
            self.compact()

    def close(self):
        self.compact()

    # -- writing --------------------------------------------------------------------------------

    def record(self, kind, ja, **fact):
        """Learn something about a name. Journalled first, applied second, so a crash between the
        two loses nothing — the journal replays on the next load."""
        fact = {k: v for k, v in fact.items() if v is not None}
        fact.setdefault("at", today())
        self._append(kind, {"ja": ja, "fact": fact})
        self._dirty += 1
        return self._apply(kind, ja, fact)

    def _apply(self, kind, ja, fact):
        cur = self.records[kind].setdefault(ja, {})
        self._merge_group(cur, fact, "en", "basis", EN_RANK, "en_conflicts")
        self._merge_group(cur, fact, "reading", "reading_basis", READING_RANK, "reading_conflicts")
        # Fields that are plain observations rather than competing claims: last writer wins, since
        # they cannot contradict each other in a way that misnames anyone.
        for k in ("ja_family", "ja_given", "reading_family", "reading_given",
                  "script", "note", "suspect_logo_title"):
            if fact.get(k) is not None:
                cur[k] = fact[k]
        for k in ("handles",):
            if fact.get(k):
                cur[k] = sorted(set(cur.get(k, [])) | set(fact[k]))
        return cur

    def _merge_group(self, cur, fact, value_key, basis_key, ranks, conflict_key):
        """Merge one competing claim (an English rendering, or a reading) under the rank rule."""
        new_val, new_basis = fact.get(value_key), fact.get(basis_key)
        if new_val is None or new_basis is None:
            return
        new_rank = ranks.get(new_basis, -1)
        old_val, old_basis = cur.get(value_key), cur.get(basis_key)
        if old_val is None:
            cur.update({value_key: new_val, basis_key: new_basis})
            self._stamp(cur, fact, value_key)
            return
        old_rank = ranks.get(old_basis, -1)
        if new_rank > old_rank:
            # The displaced claim is kept: a source we have now outranked may still be the one that
            # was right, and throwing it away makes that unrecoverable.
            self._push(cur, conflict_key, old_val, old_basis, cur.get(f"{value_key}_source"))
            cur.update({value_key: new_val, basis_key: new_basis})
            self._stamp(cur, fact, value_key)
        elif new_rank == old_rank and new_val != old_val:
            self._push(cur, conflict_key, new_val, new_basis, fact.get("source"))
        elif new_val == old_val and fact.get("source") and fact["source"] != cur.get(f"{value_key}_source"):
            # §1: corroboration from a second source is what lifts a name out of "one database says
            # so". Recorded rather than counted, so which sources agreed stays visible.
            corro = cur.setdefault(f"{value_key}_corroborated", [])
            if fact["source"] not in corro:
                corro.append(fact["source"])

    def _stamp(self, cur, fact, value_key):
        for src, dst in (("source", f"{value_key}_source"), ("source_url", f"{value_key}_url"),
                         ("at", f"{value_key}_at"), ("pass", f"{value_key}_pass")):
            if fact.get(src) is not None:
                cur[dst] = fact[src]
        if "verified" in fact and value_key == "en":
            cur["verified"] = fact["verified"]
        cur.setdefault("verified", False)

    @staticmethod
    def _push(cur, key, value, basis, source):
        entry = {"value": value, "basis": basis}
        if source:
            entry["source"] = source
        lst = cur.setdefault(key, [])
        if entry not in lst:
            lst.append(entry)

    def attempt(self, ja, pass_, source):
        """Record that `source` was ASKED about `ja` in `pass_` and answered nothing.

        Only call this on a real negative answer. See the module docstring: recording an attempt
        against a source that never replied is how a name gets permanently written off.
        """
        entry = {"pass": pass_, "source": source, "at": today()}
        self._append("attempts", {"ja": ja, "attempt": entry})
        self._dirty += 1
        self._note_attempt(ja, entry)

    def _note_attempt(self, ja, entry):
        lst = self.attempts.setdefault(ja, [])
        for e in lst:
            if e.get("pass") == entry.get("pass") and e.get("source") == entry.get("source"):
                e["at"] = entry["at"]
                return
        lst.append(entry)

    # -- reading --------------------------------------------------------------------------------

    def tried(self, ja, source):
        return any(e.get("source") == source for e in self.attempts.get(ja, ()))

    def resolved_en(self, kind, ja):
        return bool(self.records[kind].get(ja, {}).get("en"))

    def resolved_reading(self, kind, ja):
        return bool(self.records[kind].get(ja, {}).get("reading"))

    def open_for(self, kind, names, source, want="either"):
        """The names this source still has something to say about.

        `want` is what would count as progress: 'reading' for a source that gives kana, 'en' for
        one that gives an English rendering, 'either' when a hit would give both. A name already
        carrying what this source could add is skipped even though it was never attempted — that is
        §4's "resolved is final", and it is what bounds the total cost across restarts.
        """
        out = []
        for ja in names:
            if self.tried(ja, source):
                continue
            r = self.records[kind].get(ja, {})
            if want == "reading" and r.get("reading"):
                continue
            if want == "en" and r.get("en"):
                continue
            if want == "either" and r.get("en") and r.get("reading"):
                continue
            out.append(ja)
        return out

    def status(self, kind, names):
        """§4: progress legible from outside, without reading a log."""
        recs = self.records[kind]
        have_reading = sum(1 for n in names if recs.get(n, {}).get("reading"))
        have_en = sum(1 for n in names if recs.get(n, {}).get("en"))
        either = sum(1 for n in names if recs.get(n, {}).get("reading") or recs.get(n, {}).get("en"))
        attempted = sum(1 for n in names if n in self.attempts)
        conflicts = sum(1 for n in names
                        if recs.get(n, {}).get("en_conflicts") or recs.get(n, {}).get("reading_conflicts"))
        return {
            "total": len(names),
            "reading": have_reading,
            "en": have_en,
            "resolved": either,
            "attempted_only": sum(1 for n in names
                                  if n in self.attempts
                                  and not (recs.get(n, {}).get("reading") or recs.get(n, {}).get("en"))),
            "attempted": attempted,
            "remaining": len(names) - either,
            "conflicts": conflicts,
        }


HEADER_NOTE = (
    "Readings and English renderings, keyed by the exact Japanese string. NAMES-PLAN §8.1: the "
    "stored form is the KANA READING, never a romanised string — Yuri / Yuuri / Yuri are all "
    "derivable from kana and none is derivable from another, so baking one in would cap what the "
    "reader-facing style toggle can ever offer. `en` is present only where a source STATES a Latin "
    "form; otherwise it is absent and the rendering is generated from `reading` at display time. "
    "`basis` is about the English rendering (authors: stated|romaji; titles: official|translated|"
    "romaji); `reading_basis` is about the kana. Conflicts are kept, never resolved silently."
)

ATTEMPTS_NOTE = (
    "Which sources have been ASKED about which name and answered nothing. NAMES-PLAN §4: without "
    "this every restart re-pays for every miss, and the 'closed, nothing to find' bucket never "
    "populates. An entry here means the source replied and had no answer — never that a request "
    "failed or that a source was unavailable."
)
