# Standard briefing for an access audit

Give a verifier this and nothing platform-specific. It is enough to look with, and it does not hand
over the answer.

---

A reader arriving at a manga platform would expect, without being told:

- that **some chapters are free**;
- that there **may** be chapters readable for free but **rate-limited** — a limited number per day,
  per work or per account;
- that there **may** be chapters readable **only by paying**.

What varies by source, and must be read off the page rather than assumed:

- **the mechanism** — a ticket, a daily charge, a waiting period, a stated date on which the chapter
  becomes free, a subscription;
- **the details** — one per series per day, or one per account per day, or a 48-hour rental;
- **the presentation** — and this is where it goes wrong. A category may be shown as a badge, as an
  icon with no text, as a price, as a class name in the markup, or **by no adornment at all**.

> **An unmarked chapter is not an unknown chapter.** On at least one platform the middle category —
> free but rate-limited — is exactly the one with nothing next to it, while the paid ones carry a
> badge. Reading "no marker" as "paid", or as "no data", inverts the most common state on that
> platform.

So: establish what each visual state on THIS page means before classifying anything, and say which
states you found. If a page shows three distinct presentations, there are three states, whatever
they turn out to mean.

---

## Why this wording

Written after an audit where the verifier was handed one platform's access model outright. That
tests nothing: the agent confirms what it was told. The framing above supplies the *prior a reader
has* — that these three categories plausibly exist — without supplying which page shows which, so a
refutation still means something.

It also encodes the failure this project has repeated in three different places: treating the
absence of a signal as evidence of the negative. カドコミ chapters with no access data were rendered
as 有料. COMIC FUZ chapters with no badge were recorded as purchases. comici's ticket icons fell
through a two-branch test into `purchase`. Each time the fix was the same shape — find out what
unmarked means here — and each time it had to be rediscovered.
