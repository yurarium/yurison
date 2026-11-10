#!/usr/bin/env python3
"""Send a text file to the owner by email, over the SMTP account the repository secrets name.

WHY THIS EXISTS. Issues are for things that need doing (the owner, 2026-11-10). The weekly digest
is a report, so it arrives as an email instead of sitting open in the issue list.

Everything about the account and the recipient comes from the environment, so no address enters
the repository:

    MAIL_TO          where it goes
    SMTP_HOST        the submission server
    SMTP_PORT        465 for implicit TLS, anything else for STARTTLS (default 587)
    SMTP_USER        the login
    SMTP_PASSWORD    the password or app token
    MAIL_FROM        the sender, when it differs from the login

    mail.py --subject "Weekly digest: 2026-11-16" digest.md
"""
import argparse
import email.message
import os
import pathlib
import smtplib
import ssl
import sys

NEEDED = ("MAIL_TO", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD")


def missing(env):
    """The settings `env` lacks, by name. Never their values."""
    return [k for k in NEEDED if not (env.get(k) or "").strip()]


def message(subject, body, sender, to):
    m = email.message.EmailMessage()
    m["Subject"] = subject
    m["From"] = sender
    m["To"] = to
    m.set_content(body)
    return m


def send(m, host, port, user, password, smtp=smtplib):
    """Deliver `m`. Port 465 speaks TLS from the start; any other port upgrades with STARTTLS."""
    context = ssl.create_default_context()
    if port == 465:
        with smtp.SMTP_SSL(host, port, context=context, timeout=60) as s:
            s.login(user, password)
            s.send_message(m)
    else:
        with smtp.SMTP(host, port, timeout=60) as s:
            s.starttls(context=context)
            s.login(user, password)
            s.send_message(m)


def main(argv=None, env=None, smtp=smtplib):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", required=True)
    ap.add_argument("body", help="the text file to send")
    a = ap.parse_args(argv)
    lack = missing(env)
    if lack:
        print(f"mail: not configured; set {', '.join(lack)} in the repository secrets",
              file=sys.stderr)
        return 2
    m = message(a.subject, pathlib.Path(a.body).read_text(encoding="utf-8"),
                env.get("MAIL_FROM") or env["SMTP_USER"], env["MAIL_TO"])
    send(m, env["SMTP_HOST"], int(env.get("SMTP_PORT") or 587),
         env["SMTP_USER"], env["SMTP_PASSWORD"], smtp)
    print(f"mail: sent {a.subject!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
