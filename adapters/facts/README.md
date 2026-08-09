# facts

One module per fact, where a fact is anything two places in the codebase can disagree about.

Each module has a single public entry point, owns the checks about its own subject, and states what
it cannot see in `BLINDSPOT.md`. Nothing outside a module may name its internals; `adapters/lint/`
proves it.

Where a fact has a fuzzy edge it belongs to whoever can DECIDE it, and everyone else consumes the
decision. The plan and the extraction protocol are in `docs/REFACTOR-PLAN.md`.
