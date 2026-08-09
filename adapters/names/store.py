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

# `publishers` is a third kind and not a third store. A publisher name is a name: it is rendered in
# English on the same page, from the same file, with the same basis and the same source travelling
# beside it. It arrived because the interface was carrying seven of them as a literal while the
# corpus held 389, and a literal has nowhere to put the page a name was read from.
KINDS = ("authors", "titles", "publishers")

# How much a claim outranks another claim about the same field. Higher wins; equal-and-different is
# a conflict, never a silent overwrite.
EN_RANK = {
    # authors (§5): the person's own rendering beats anything we compute from a reading.
    "stated": 30,
    # TITLES. Three levels, not two, per the project owner's correction to §5:
    #   official-jp  the English title the AUTHOR, MAGAZINE or JAPANESE PUBLISHER uses. It is the
    #                work's own name in English and outranks everything.
    #   licensed     what an English-language licensor publishes it as. Authoritative, but a second
    #                party's choice, so it loses to the work's own.
    #   translated / romaji  ours, and marked as ours.
    "official-jp": 50,
    "licensed": 40,
    "translated": 20,
    "romaji": 10,
}

# Where a claim came from, kept beside every claim so that "who says so" survives into the data.
# The distinction that matters is the last two: a community-editable database is a lead, not an
# attribution, and only a Japanese publisher page or a licensor catalogue can promote a title out
# of candidacy.
SOURCE_KINDS = ("platform", "publisher-jp", "licensor", "community-db", "derived")

READING_RANK = {
    "surface": 50,        # the name is written in kana; the reading is not inferred, it is the name
    "stated": 40,         # a source gives kana explicitly (MADB yomi, an NDL heading, a byline gloss)
    # A reading a REVIEWER settled from the best evidence available, where no source states it
    # outright. Below `stated` because nobody printed it, above `aligned` because a person weighed
    # what a machine could only align: the compound, the register, how the work is spoken about.
    # It carries a note saying what it rests on, which is the difference between this and a guess.
    "researched": 30,
    # A COMMUNITY DATABASE PRINTS THE KANA and nobody with standing over the name has spoken.
    # Wikidata's P1814, ruled noncanonical by the project owner on 2026-08-09 and admitted as a
    # floor: above the machine work below it because an editor typed the kana, below `researched`
    # because nobody weighed anything. `curate.READING_ATTRIBUTION` carries the argument.
    "community-printed": 25,
    "aligned": 20,        # derived by aligning a whole-string reading against the surface (§5c)
    "back-converted": 10,  # recovered from a romanised string, lossy in the long vowels (§8.1)
    "guessed": 0,         # pass 4's business; never produced by passes 0-2
}


def today():
    return datetime.date.today().isoformat()


def days_since(stamp):
    """Days since an `at` date. An unreadable or missing one counts as today, so it never expires.

    Failing towards "recent" is the safe direction here: it makes the attempt keep suppressing the
    question, which costs a lookup nobody makes. Failing the other way would re-ask a two hour
    sweep every run because one date was written badly.
    """
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(str(stamp))).days
    except (TypeError, ValueError):
        return 0


def same_reading(a, b):
    """Are these the same reading, ignoring where the word boundary was drawn?

    アオタユキコ and アオタ ユキコ are one reading written two ways: a kana surface has no space in
    it, and a source that separates family from given does. Calling that a conflict would fill the
    file with 23 disagreements that are not disagreements, and — worse — would train whoever reads
    the conflict list to skim it. The list is only useful if everything in it is real.

    The spacing itself is not discarded: where a source distinguishes the halves they are stored in
    reading_family and reading_given, which is where §8.2 wants them anyway.
    """
    return str(a).replace(" ", "").replace("　", "") == str(b).replace(" ", "").replace("　", "")


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

    def drop_stale_spans(self):
        """Remove furigana spans that no longer spell the reading they sit beside.

        Clearing them as a reading is replaced only helps from now on, and the file already held
        193 records whose ruby said something their own reading did not. Swept at write time so the
        file heals rather than needing a migration, and so a pass that forgets to clear them cannot
        quietly reintroduce the state.
        """
        import kana  # local: the store is imported by passes that kana does not need
        dropped = 0
        for kind in KINDS:
            for rec in self.records[kind].values():
                spans, reading = rec.get("furigana_spans"), rec.get("reading")
                if not spans or not reading:
                    continue
                try:
                    ok = kana.ruby_spells(spans, reading)
                except (TypeError, IndexError):
                    ok = False
                if not ok:
                    rec.pop("furigana_spans", None)
                    dropped += 1
        return dropped

    def drop_settled_doubt(self):
        """Remove the uncertain mark from readings that are no longer the analyser's.

        The mark says a machine was unsure, and it is set on the record rather than passed through
        record(), so a better reading arriving later left it in place: eight titles a person had
        settled stayed in the review queue, and a budget that cannot fall is not a ratchet. Swept
        at write time, so it heals whatever route replaced the reading.
        """
        cleared = 0
        for kind in KINDS:
            for rec in self.records[kind].values():
                if (rec.get("reading_uncertain")
                        and rec.get("reading_basis") not in ("analyser", "back-converted")):
                    rec.pop("reading_uncertain", None)
                    cleared += 1
        return cleared

    def drop_spacing_conflicts(self):
        """Remove conflict entries that agree with the reading they are filed against.

        THE THIRD PLACE THAT ASKED `==` WHERE IT SHOULD ASK `same_reading`. That function exists
        so a word boundary is not read as a disagreement, and its own docstring records what
        ignoring it costs: a list nobody trusts is a list nobody reads. `_merge_group` gates two of
        its three pushes on it and left the third ungated, so every reading an analyser wrote
        first and a source then improved filed the analyser's spelling as a disagreement with the
        answer. sudachi tokenises 4kaエンピツ as `4 ka エンピツ` where openBD states `4ka エンピツ`,
        and the store called that a conflict 1,022 times.

        565 of the 1,142 entries on disk were this. Swept at write time rather than by a migration,
        for the reason the two sweeps above are: the file heals, and a pass that reintroduces the
        state cannot leave it behind.

        THE SPACING ITSELF IS NOT LOST. Where a source divides a name the halves are stored in
        `reading_family` and `reading_given`, which is where §8.2 wants them.
        """
        dropped = 0
        for kind in KINDS:
            for rec in self.records[kind].values():
                held = rec.get("reading")
                lst = rec.get("reading_conflicts")
                if not held or not lst:
                    continue
                kept = [c for c in lst if not same_reading(str(c.get("value") or ""), held)]
                dropped += len(lst) - len(kept)
                if kept:
                    rec["reading_conflicts"] = kept
                else:
                    rec.pop("reading_conflicts", None)
        return dropped

    def compact(self):
        """Write the YAML from memory, then drop the journal it superseded."""
        self.drop_stale_spans()
        self.drop_settled_doubt()
        self.drop_spacing_conflicts()
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
            os.chmod(tmp, 0o644)  # mkstemp is 0600; these are data files like every other in data/
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
        superseding = fact.pop("supersede", None)
        if superseding:
            self._supersede(cur, fact)
        self._merge_group(cur, fact, "en", "basis", EN_RANK, "en_conflicts")
        _reading_was = cur.get("reading")
        self._merge_group(cur, fact, "reading", "reading_basis", READING_RANK, "reading_conflicts",
                          equiv=same_reading)
        # SPANS BELONG TO THE READING THEY WERE CUT FROM. pass 4 writes furigana_spans beside the
        # reading it derived them from, and nothing dropped them when a better reading replaced it,
        # so 193 records held ruby spelling something their own reading no longer said. build.py
        # notices and re-derives, which is why the page was right while the file was not; a record
        # that contradicts itself is still a record nobody can trust at a glance.
        if cur.get("reading") != _reading_was:
            cur.pop("furigana_spans", None)
        # Fields that are plain observations rather than competing claims: last writer wins, since
        # they cannot contradict each other in a way that misnames anyone.
        # `translation_note` is here and not on the claim because `en_conflicts` holds a value, a
        # basis and a source and nothing else. Our translation of a title that already carries the
        # publisher's English is a losing claim by rank, so the argument for it has no home on the
        # claim itself, and a translation with no argument behind it is the machine translation
        # NAMES-PLAN §5a rules out. It cannot collide with `note`, which belongs to the attributed
        # name and says which page that was read from.
        for k in ("ja_family", "ja_given", "reading_family", "reading_given",
                  "script", "note", "translation_note", "suspect_logo_title"):
            if fact.get(k) is not None:
                cur[k] = fact[k]
        for k in ("handles",):
            if fact.get(k):
                cur[k] = sorted(set(cur.get(k, [])) | set(fact[k]))
        if fact.get("candidate"):
            self._add_candidate(cur, fact)
        # A CITATION IS NOT A COMPETING CLAIM, so recording one must not depend on the claim
        # changing. `_merge_group` stamps only where it accepts a new value, which is right for a
        # source arguing about a reading and wrong for a reviewer writing down the page an
        # already-agreed reading came from: the 11 BOOK☆WALKER addresses landed on records that
        # already said フレナイ, the merge read it as agreement, and nothing was stamped. The
        # curated file is the decision of record, which is what `supersede` says, so its provenance
        # lands on whatever it and the record now agree about.
        if superseding:
            for value_key, agrees in (("en", lambda a, b: a == b), ("reading", same_reading)):
                held, given = cur.get(value_key), fact.get(value_key)
                if held is not None and given is not None and agrees(held, given):
                    self._stamp(cur, fact, value_key)
        self._verify(cur)
        return cur

    def _supersede(self, cur, fact):
        """Let a reviewer revise their own earlier decision.

        The rank rule treats an equal-ranked different value as a conflict and keeps the older one,
        which is right when two SOURCES disagree: picking quietly is how a person gets misnamed.
        It is wrong when the two claims are the same producer changing its mind. Revising a
        translation in curated.yaml applied cleanly, filed the new wording as a conflict against
        itself, and left the page showing the wording that had just been rejected.

        So this clears the slot first, and only for a caller that says it is superseding. The old
        value still goes to the conflict list, because a title that was considered and dropped is
        worth being able to search for, and because the audit trail is the point of the file.

        WHAT IS THE SAME READING IS `same_reading`'s ANSWER HERE TOO. This asked `==`, which is a
        second opinion on a question that function exists to settle, and the two disagree on exactly
        the case its docstring is about: アオノナチ against アオノ ナチ is one reading with the
        division supplied. 37 kana names took a division from openBD's collationkey and each filed
        its own undivided form as a disagreement with itself. A conflict list is only read if
        everything in it is a real conflict.
        """
        for value_key, basis_key, conflict_key, agrees in (
                ("en", "basis", "en_conflicts", None),
                ("reading", "reading_basis", "reading_conflicts", same_reading)):
            new = fact.get(value_key)
            old = cur.get(value_key)
            # A CITATION THE FILE NO LONGER CARRIES LEAVES THE RECORD, and this runs before the
            # early exit below because the value staying the same is exactly when it was needed.
            # record() drops every None before _apply is reached, which is right for a pass saying
            # only what it learned and wrong for the file that is the decision of record: a
            # source_url deleted from an entry stayed in the store, and re-applying could not
            # remove it. 真先輩の前ではかっこつけられない! cited the National Diet Library for OUR
            # translation because the address had first been written in the entry-wide field, and
            # moving it to reading_url left the wrong one behind for anyone to read.
            #
            # Only for a claim the file actually makes. An entry that says nothing about a reading
            # is not asking for the reading's citation to be thrown away.
            if new is not None:
                for shared, dst in self._stamped(value_key):
                    if shared in ("at", "pass") or dst in fact or shared in fact:
                        continue
                    cur.pop(dst, None)
            # A REVISED BASIS IS A REVISED DECISION EVEN WHERE THE STRING IS UNCHANGED, which this
            # did not see: it compared values, so a reviewer correcting `licensed` to `translated`
            # on the same wording reached the store as agreement and the store went on saying
            # licensed. `新・魔法科高校の劣等生 キグナスの乙女たち` was in that state, filed as a
            # licensor's name while its own note says the rendering is ours, and the rank rule
            # cannot correct it: `translated` ranks below `licensed`, so the file's answer could
            # only ever lose. The curated file is the decision of record and that includes what
            # kind of claim it is.
            rebasing = (fact.get(basis_key) is not None and cur.get(basis_key) is not None
                        and fact[basis_key] != cur.get(basis_key))
            if new is None or old is None or (new == old and not rebasing):
                continue
            # Nothing goes to the conflict list when the two agree about the string. A rebase
            # revises how one claim is justified; it does not produce a second claim to disagree
            # with, and filing one would be the conflict list disagreeing with itself.
            if new != old and not (agrees and agrees(new, old)):
                self._push(cur, conflict_key, old, cur.get(basis_key),
                           cur.get(f"{value_key}_source"))
            cur.pop(value_key, None)
            cur.pop(basis_key, None)
            # AND THE CITATION OF THE CLAIM BEING REPLACED. Leaving it standing means the incoming
            # claim inherits whatever page the old one was read from wherever the new one supplies
            # none, so a reviewer replacing a sourced reading with their own reasoning would ship
            # their judgement wearing somebody else's URL. Same fault as the refutation that kept
            # its address, arriving by the other door.
            for _shared, dst in self._stamped(value_key):
                cur.pop(dst, None)
            # A conflict list that still holds the value now being adopted reads as a disagreement
            # with itself, and would be shown as one.
            kept = [c for c in cur.get(conflict_key, []) if c.get("value") != new]
            if kept or conflict_key in cur:
                cur[conflict_key] = kept
            if conflict_key in cur and not cur[conflict_key]:
                cur.pop(conflict_key)

    @staticmethod
    def _add_candidate(cur, fact):
        """An English title we hold but cannot attribute — recorded, never promoted to `en`.

        The project owner's correction to §5: a community-editable database (Wikidata, AniList,
        MangaUpdates) may be reporting a licensed title, a Japanese publisher's own English title,
        or a SCANLATION title, and nothing in the record distinguishes them. A scanlation title is
        not a name the work has, so publishing one — even marked — would be inventing a name and
        attributing it to the book. Candidacy is the honest state: we have seen this string, we
        cannot yet say who gave the work that name, and one fetch of the licensor page it points at
        would settle it.
        """
        entry = {"value": fact["candidate"], "source": fact.get("source")}
        for k in ("source_kind", "source_url", "candidate_note"):
            if fact.get(k):
                entry[k.replace("candidate_", "")] = fact[k]
        lst = cur.setdefault("en_candidates", [])
        if not any(e.get("value") == entry["value"] and e.get("source") == entry.get("source")
                   for e in lst):
            lst.append(entry)

    def _merge_group(self, cur, fact, value_key, basis_key, ranks, conflict_key, equiv=None):
        """Merge one competing claim (an English rendering, or a reading) under the rank rule.

        A claim may carry a basis with NO value, and that is the normal case for an author: §8.1
        says the romanisation is generated per reader from the kana rather than stored, so
        `basis: romaji` with no `en` means exactly "render it from the reading". Requiring a value
        here would have thrown that claim away and left every romanised author with no basis at all
        — which is the field §1 needs in order to know what a later pass must not overwrite.
        """
        new_basis = fact.get(basis_key)
        if new_basis is None:
            return
        new_val = fact.get(value_key)
        new_rank = ranks.get(new_basis, -1)
        agrees = equiv or (lambda a, b: a == b)
        if basis_key not in cur:
            if new_val is not None:
                cur[value_key] = new_val
            cur[basis_key] = new_basis
            self._stamp(cur, fact, value_key)
            return
        old_val, old_basis = cur.get(value_key), cur.get(basis_key)
        old_rank = ranks.get(old_basis, -1)
        if new_val is None and old_val is not None:
            # A bare basis — "render this from the reading" — cannot relabel a string somebody
            # else supplied. Letting it through would stamp `official-jp` onto a romanisation
            # without changing the romanisation, which is the worst of both: a wrong string wearing
            # a basis that §5 shows unmarked.
            return
        if new_rank > old_rank:
            # The displaced claim is kept: a source we have now outranked may still be the one that
            # was right, and throwing it away makes that unrecoverable.
            #
            # UNLESS THE TWO AGREE, and this branch was the one place that did not ask. The other
            # two pushes below both consult `agrees`, which for a reading is `same_reading` and
            # exists so a word boundary is not read as a disagreement. Here a better source
            # arriving filed the reading it CONFIRMED as a conflict with itself: sudachi writes
            # `4 ka エンピツ` and openBD states `4ka エンピツ`, and 508 author readings and 57
            # titles were recorded as contradictions of the answer they agree with.
            if old_val is not None and not (new_val is not None and agrees(new_val, old_val)):
                self._push(cur, conflict_key, old_val, old_basis, cur.get(f"{value_key}_source"))
            if new_val is not None:
                cur[value_key] = new_val
            cur[basis_key] = new_basis
            self._stamp(cur, fact, value_key)
        elif new_rank < old_rank and new_val is not None and not agrees(new_val, old_val):
            # The new claim loses, and is kept anyway. The project owner's correction is explicit:
            # "where a work has both an official-jp and a licensed title and they differ, keep both
            # and prefer official-jp for display. Do not silently discard the loser." A licensor's
            # title is a real fact about the work even when the work's own English name outranks it.
            self._push(cur, conflict_key, new_val, new_basis, fact.get("source"))
        elif new_rank == old_rank and old_val is None and new_val is not None:
            # Same rank, but the existing claim was a bare basis with no string — an author marked
            # `romaji` because their reading is known. A source now offering an actual string is
            # adding to that claim, not competing with it, so it fills the gap rather than being
            # dropped on the floor as a tie.
            cur[value_key] = new_val
            self._stamp(cur, fact, value_key)
        elif (new_rank == old_rank and new_val is not None and old_val is not None
              and not agrees(new_val, old_val)):
            self._push(cur, conflict_key, new_val, new_basis, fact.get("source"))
        elif (new_val is not None and old_val is not None and agrees(new_val, old_val)
              and fact.get("source")
              and fact["source"] != cur.get(f"{value_key}_source")):
            # §1: corroboration from a second source is what lifts a name out of "one database says
            # so". Recorded rather than counted, so which sources agreed stays visible.
            corro = cur.setdefault(f"{value_key}_corroborated", [])
            if fact["source"] not in corro:
                corro.append(fact["source"])

    def _stamp(self, cur, fact, value_key):
        """Attach provenance to the CLAIM, not to the record.

        `source_kind` was briefly a record-level field and that was wrong in a way worth keeping a
        note about: `Sal Jiang` had its `platform` provenance — the Japanese site's own byline —
        overwritten with `community-db` by a MangaUpdates record that merely corroborated the same
        string. The record then said a platform-printed name came from a fan database. The owner's
        correction asks for provenance "per title, not just the string", and a record can hold two
        claims from two kinds of source, so the stamp has to travel with each claim.
        """
        for src, dst in self._stamped(value_key):
            # THE CLAIM'S OWN CITATION OUTRANKS THE ENTRY'S, and the key that carries it is the
            # field it writes: a fact giving `reading_url` is citing the reading, while one giving
            # `source_url` is citing whatever the entry is mainly about.
            #
            # One curated entry holds two claims and had one citation between them. A title whose
            # English was translated here and whose reading was read off a shop page carried
            # `source: yurarium, source_kind: derived` for the translation, and the reading was
            # stamped with it. 11 titles said a source stated their reading while naming us as
            # the source and holding no page at all. The reading_note beside them named
            # BOOK☆WALKER, which is where they really came from, and nothing could act on prose.
            val = fact.get(dst) if src is None else fact.get(dst, fact.get(src))
            if val is not None:
                cur[dst] = val

    @staticmethod
    def _stamped(value_key):
        """(the entry-wide key, the field this claim writes) for every part of a citation.

        Named once because the stamp writes them, `clear_claim` removes them, and `provenance.cite`
        reads them back. A fourth copy of this list is how a refutation came
        to leave a URL behind.
        """
        return (("source", f"{value_key}_source"), ("source_url", f"{value_key}_url"),
                ("source_kind", f"{value_key}_source_kind"),
                ("at", f"{value_key}_at"), ("pass", f"{value_key}_pass"),
                # WHEN A PERSON LAST LOOKED, which `at` was standing in for and cannot mean. `at`
                # is the day the fact was written, and a pass writes one on every run, so a
                # machine's run date and a reviewer's decision were the same field wearing one
                # name. A reading that says a human settled it has to be able to say when.
                ("reviewed", f"{value_key}_reviewed"),
                # NO ENTRY-WIDE FALLBACK, which is what the None says. A record-level `note`
                # describes the entry and is stored as itself; only a note written about THIS
                # claim belongs to it. 814 curated `reading_note` values carry the argument behind
                # every hand-settled reading, and the thing `researched` is required to supply.
                # Each was built into the fact and then matched by nothing, so they reached no store,
                # no build and no reader.
                (None, f"{value_key}_note"),
                # WHERE THE DIVISION CAME FROM, WHICH IS A SECOND FACT ABOUT A READING AND HAS TO
                # BE A FIELD. `boundary.fill` writes `reading_boundary` and `ndl_heading.entry`
                # wrote the same fact into `reading_note`, so 212 records cited their division in
                # prose and any check reading the field believed they had no source. No entry-wide
                # fallback, for the same reason the note has none: an entry-level citation is about
                # whatever the entry is mainly for, and this belongs to the reading alone.
                (None, f"{value_key}_boundary"))

    # The rest of what belongs to one claim: its value, how it is justified, and the working that
    # was kept beside it. Everything here dies with the claim.
    CLAIM_PARTS = {
        "en": ("en", "basis", "en_conflicts", "en_corroborated"),
        "reading": ("reading", "reading_basis", "reading_conflicts", "reading_corroborated",
                    "reading_family", "reading_given", "reading_uncertain", "furigana_spans"),
    }

    def clear_claim(self, kind, ja, value_key):
        """Remove a claim and everything hanging off it. Returns the fields actually dropped.

        A REFUTATION THAT LEAVES THE CITATION BEHIND IS WORSE THAN NO REFUTATION. curate.py popped
        a hand-written list of fields, and it was short: 11 refuted author readings kept
        `reading_source: sudachi` and a date for a reading that no longer existed, and two kept a
        `reading_url` pointing at the MangaUpdates page for a DIFFERENT PERSON, which is the exact
        page the refutation was written to disown. 古川楊也 was published as HOSHINO Katsura and the record
        went on citing the page that said so.

        `reading_family` and `reading_given` were in the same state: 古川楊也 kept フルカワ / ヨヤ,
        which are halves of the reading that was withdrawn.
        """
        rec = self.records[kind].get(ja)
        if not rec:
            return []
        fields = list(self.CLAIM_PARTS.get(value_key, (value_key,)))
        fields += [dst for _shared, dst in self._stamped(value_key)]
        dropped = [f for f in fields if rec.pop(f, None) is not None]
        self._verify(rec)
        return dropped

    @staticmethod
    def _verify(cur):
        """`verified` is derived, never passed in, and it is about the READING.

        §5d is specific: "readings carry verified: true|false", and the mark exists so that a real
        person is not authoritatively misnamed. That is a fact about the kana, not about the English
        rendering — whose status is what `basis` already carries (§5's table). Keeping them as one
        flag each, with one meaning each, is what stops the two marks being conflated later by
        someone reading only half the plan.

        Deriving rather than storing it means it cannot drift out of step with the reading it
        describes: a better source arriving raises reading_basis and the flag follows in the same
        write.

        A name already written in Latin has no reading to verify and is not unverified: the platform
        printed the author's own form, and there is nothing left to be wrong about.
        """
        if cur.get("reading"):
            cur["verified"] = cur.get("reading_basis") in ("surface", "stated")
        elif cur.get("en") and cur.get("basis") in ("stated", "official-jp", "licensed"):
            cur["verified"] = True
        else:
            cur["verified"] = False

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

        `pass_` MAY BE None, AND IS FOR A ROUTE THAT IS NOT ONE OF THE FOUR. The field exists to
        say which of NAMES-PLAN §4's numbered passes did the asking. `ndl-books` is not one of
        them, and writing its own name into both fields would state the same fact twice, which is
        the shape §3 is about. The key is left out entirely so the file does not fill with nulls.
        """
        entry = {"source": source, "at": today()}
        if pass_ is not None:
            entry["pass"] = pass_
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

    def tried(self, ja, source, stale_after_days=None):
        """Whether `source` has already been asked about `ja` and answered nothing.

        `stale_after_days` lets an absence expire. A CATALOGUE ABSENCE IS NOT PERMANENT: a work
        with no record at the National Diet Library today gets one when its next volume is
        deposited, and a book openBD has never carried gets registered when the publisher files it.
        An attempt with no expiry answers "we asked once, in 2026" for ever, which turns a saving
        into a hole nothing can fill.

        THE DEFAULT IS STILL FOR EVER, and deliberately. The four numbered passes were written
        against `resolved is final` and their sources are community databases whose answer for a
        name does not change on a schedule; expiring those would re-ask 2,002 names against
        Wikidata every few months for almost nothing. The callers that pay per request pass a
        number, and each says why it chose that one.
        """
        for e in self.attempts.get(ja, ()):
            if e.get("source") != source:
                continue
            if stale_after_days is None:
                return True
            if days_since(e.get("at")) < stale_after_days:
                return True
        return False

    def supplies(self, kind, ja, want):
        """Does this record now carry what a source promising `want` was supposed to add?

        The mirror of open_for's test, and it has to stay the mirror: drive() uses this to decide
        whether a name was actually answered, and open_for uses the same rule to decide whether to
        ask again. If they disagree, a name is either asked forever or never asked again.
        """
        r = self.records[kind].get(ja) or {}
        if want == "reading":
            return bool(r.get("reading"))
        if want == "en":
            return bool(r.get("en"))
        return bool(r.get("reading")) and bool(r.get("en"))

    def resolved_en(self, kind, ja):
        return bool(self.records[kind].get(ja, {}).get("en"))

    def resolved_reading(self, kind, ja):
        return bool(self.records[kind].get(ja, {}).get("reading"))

    def open_for(self, kind, names, source, want="either", stale_after_days=None):
        """The names this source still has something to say about.

        `want` is what would count as progress: 'reading' for a source that gives kana, 'en' for
        one that gives an English rendering, 'either' for a source that might give one or the
        other — in which case it still has something to offer until BOTH are held. A name already
        carrying what this source could add is skipped even though it was never attempted; that is
        §4's "resolved is final", and it is what bounds the total cost across restarts.
        """
        out = []
        for ja in names:
            if self.tried(ja, source, stale_after_days):
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
    "`basis` is about the English rendering (authors: stated|romaji; titles: official-jp|licensed|"
    "translated|romaji, in that precedence); `reading_basis` is about the kana. `en_candidates` "
    "holds English titles we have seen but cannot attribute to a Japanese publisher or a licensor: "
    "community databases also carry scanlation titles, which are not names the work has, so a "
    "candidate is never promoted to `en` without confirmation. Conflicts are kept, never resolved "
    "silently."
)

ATTEMPTS_NOTE = (
    "Which sources have been ASKED about which name and answered nothing. NAMES-PLAN §4: without "
    "this every restart re-pays for every miss, and the 'closed, nothing to find' bucket never "
    "populates. An entry here means the source replied and had no answer, never that a request "
    "failed or that a source was unavailable. `at` is what an expiry is measured from: a catalogue "
    "absence is a fact about today, and the routes that pay per request re-ask once it is old "
    "enough. See NameStore.tried."
)
