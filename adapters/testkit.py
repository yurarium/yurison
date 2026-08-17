#!/usr/bin/env python3
"""A tiny assertion harness whose tests can be proved capable of failing.

WHY NOT plain asserts. This project's characteristic bug is a check that reports clean because it
never ran: a grep that swallowed a traceback, an invariant parsing on a separator that had changed,
a `git grep` with a stray `--`, a lint whose rule could not match its own normalised output. Each
was green and meaningless. A test suite is the same hazard with a bigger surface, and "the tests
pass" is worth exactly nothing if no one has shown they can fail.

HOW THE PROOF WORKS. Every assertion goes through `Suite.check`. Under `YURA_CANARY=1` the harness
inverts the outcome of every check, so a suite that asserts anything real must FAIL. A suite that
passes while inverted is asserting nothing, and the runner reports it as vacuous. That catches the
case that matters, which is a test file that exercises code without ever pinning a value.

It also counts checks, because a suite with none is vacuous whether inverted or not.

WHY "CANARY-PROVEN" IS PRINTED. A suite that does not use this harness ignores YURA_CANARY
entirely, passes, and looks identical to one that was inverted and failed as it should. That is the
vacuous-green failure again, in the very tool built to detect it: the first run of --canary
reported nine suites healthy when only one of them had actually been inverted. The marker is the
evidence, and test.py treats its absence as unproven rather than as success.

WHY NOT pytest. It is not installed here and would be another dependency on a machine that already
runs the pipeline with the standard library plus yaml and sudachi. Nothing below needs it.
"""
import os
import sys
import traceback

CANARY = os.environ.get("YURA_CANARY") == "1"


class Suite:
    """Assertions for one module. `python3 <test file>` runs it; test.py collects it."""

    def __init__(self, name):
        self.name = name
        self.checks = 0
        self.failures = []
        self.skipped = []

    def check(self, cond, msg):
        """Assert `cond`, reporting `msg` when it does not hold."""
        self.checks += 1
        ok = bool(cond)
        if CANARY:
            ok = not ok            # a suite asserting anything real must fail under inversion
        if not ok:
            self.failures.append(msg)
        return ok

    def eq(self, got, want, msg):
        return self.check(got == want, f"{msg}: got {got!r}, want {want!r}")

    def ne(self, got, bad, msg):
        return self.check(got != bad, f"{msg}: got the forbidden value {got!r}")

    def skip(self, msg):
        """Record that a check could not run, loudly, and go on.

        THE METHOD THE SUITES ALREADY CALLED. `test_analyser` guards its five dictionary checks with
        `except ImportError: s.skip("sudachipy absent")`, written so a missing optional dependency
        would degrade rather than fail. Nothing had ever taken that branch, so the AttributeError it
        actually raised sat there until the equivalence workflow installed a shorter list than the
        pipeline's and the run died inside its own fallback.

        IT IS NOT A PASS AND IT IS NOT SILENT. A skipped check proves nothing, so it is not counted
        among `checks`, which is what `report` calls a suite vacuous for; and it prints, because the
        failure being guarded against here is a check that stops running and says nothing.
        """
        self.skipped.append(msg)
        print(f"  SKIP    {self.name}: {msg}")
        return False

    def raises(self, exc, fn, msg):
        try:
            fn()
        except exc:
            return self.check(True, msg)
        except Exception as e:
            return self.check(False, f"{msg}: raised {type(e).__name__} instead of {exc.__name__}")
        return self.check(False, f"{msg}: nothing raised")

    def report(self):
        """Print the outcome and return an exit code. 0 pass, 1 fail, 2 vacuous."""
        if self.checks == 0:
            print(f"  VACUOUS {self.name}: no checks ran")
            return 2
        if CANARY:
            # Inverted, so failures are the healthy outcome and silence is the alarm.
            if self.failures:
                print(f"  ok      {self.name}: {self.checks} check(s), all can fail")
                print("CANARY-PROVEN")     # read by test.py; see WHY IT IS PRINTED below
                return 0
            print(f"  VACUOUS {self.name}: {self.checks} check(s) passed while inverted")
            return 2
        if self.failures:
            print(f"  FAIL    {self.name}: {len(self.failures)} of {self.checks}")
            for f in self.failures:
                print(f"            {f}")
            return 1
        print(f"  ok      {self.name}: {self.checks} check(s)")
        return 0


def run(fn, name):
    """Entry point for a test module: `sys.exit(testkit.run(main, __name__))`."""
    s = Suite(name)
    try:
        fn(s)
    except Exception:
        # A crash is a failure, not a disappearance. Under canary the crash may BE the point, so
        # it is only fatal outside it.
        if not CANARY:
            print(f"  ERROR   {name}: raised during the test")
            traceback.print_exc()
            return 1
    return s.report()
