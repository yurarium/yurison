#!/usr/bin/env python3
"""What each budget measures, and the record of every rise accepted as arrivals.

WHY THIS EXISTS. Every data budget used to block `./check.py --gate` the moment it rose, whatever it
counted. Most of them count a queue that grows with the corpus by design: a new author arrives with
a reading no source states, a new work with a romanisation nobody has replaced. A rise there is the
corpus growing, and it stopped the person or the job that happened to be committing next until
somebody wrote "new works arrived" into a commit message. LAUNCH-PLAN section 4 sorts them:

  regression  a known good thing got worse: a page losing its English, a credit losing its works.
              Strict, as before. Every budget not named below is one, so a new budget is strict
              until somebody argues otherwise.
  arrival     a queue new works and authors join. A rise is accepted at the gate, its value
              recorded, and a line written to `data/ledger/budget-arrivals.jsonl` saying how far it
              rose and how far the corpus grew since the last acceptance, which the weekly digest
              totals. Falls are banked as before, so the number still ratchets down as the queue
              is worked.
  report      a number with no direction anybody is working it in. Measured and shown, never a
              failure, never ratcheted.

The source budgets in check.py's SOURCE_BUDGETS count this repository's code and stay strict.
"""
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "ledger" / "budget-arrivals.jsonl"

ARRIVAL = frozenset({
    "author names romanised as one word",
    "author readings no source states",
    "an imprint field repeating its publisher",
    "citations withheld from readers",
    "credit fields an identifier does not cover",
    "credits the corpus files as a venue",
    "divisions resting on a community database",
    "imprint strings that reach no line",
    "kana names with no stated division",
    "macron boundaries nobody has ruled on",
    "nicovideo works with no rights",
    "publisher readings nobody has settled",
    "rows with a moving address",
    "ruby asserting a reading per character",
    "scope questions left open",
    "titles read by a machine, unmarked",
    "titles showing a romanisation nobody has ruled on",
    "uncertain readings",
    "undated cmoa candidates",
    "unreadable bookwalker rows",
    "updates naming a work we do not hold",
    "volume rows with no publication date",
    "works holding fewer volumes than the shop states",
    "works showing a romanisation",
})

REPORT = frozenset({
    "predicted updates already behind the run",
    "readings an analyser no longer installed produced",
    "targets a capture wrote no row for",
    "works holding more volumes than the shop states",
    "works whose first publication country is unattested",
})


def kind(name):
    """`arrival`, `report` or `regression`."""
    if name in ARRIVAL:
        return "arrival"
    if name in REPORT:
        return "report"
    return "regression"


def last_corpus(lines):
    """`{budget: corpus}` at each budget's latest accepted rise, from the ledger's lines."""
    out = {}
    for line in lines:
        try:
            e = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(e, dict) and e.get("budget"):
            out[e["budget"]] = e.get("corpus") or {}
    return out


def reason(name, was, now, corpus, before=None):
    """The sentence an accepted rise is recorded with."""
    grew = []
    for k in ("works", "credits"):
        if before and before.get(k) is not None and corpus.get(k) is not None:
            d = corpus[k] - before[k]
            grew.append(f"{d:+d} {k}")
    since = (f"while the corpus moved {', '.join(grew)} since its last accepted rise" if grew
             else f"with the corpus at {corpus.get('works')} works and {corpus.get('credits')} "
                  f"credits, the first rise recorded for it")
    return f"{name} rose {was} -> {now} ({now - was:+d}) {since}"


def accept(rises, corpus, ledger=LEDGER, today=None):
    """Write one ledger line per `(name, was, now)` and return the reasons, in order."""
    ledger = pathlib.Path(ledger)
    before = last_corpus(ledger.read_text(encoding="utf-8").splitlines()) if ledger.exists() else {}
    day = today or datetime.date.today().isoformat()
    lines, out = [], []
    for name, was, now in rises:
        why = reason(name, was, now, corpus, before.get(name))
        out.append(why)
        lines.append(json.dumps({"date": day, "budget": name, "was": was, "now": now,
                                 "corpus": corpus, "reason": why}, ensure_ascii=False))
    if lines:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return out


def corpus_of(ctx):
    """`{works, credits}` live in the registries the gate already loaded."""
    works = [w for w in ctx.get("identity") or [] if not w.get("merged_into")]
    credits = [c for c in (ctx.get("credits") or {}).get("credits") or [] if not c.get("merged_into")]
    return {"works": len(works), "credits": len(credits)}
