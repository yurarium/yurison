#!/usr/bin/env python3
"""mail.py: the digest goes out over the configured account, and an unconfigured one says what is missing.

COVERS = ['adapters/mail.py']
"""
import contextlib
import io
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import mail                                                             # noqa: E402


class FakeSMTP:
    """Records what a session did, in place of the smtplib module."""

    def __init__(self):
        self.log = []

    def _session(self, kind):
        log = self.log

        class Session:
            def __init__(self, host, port, **kw):
                log.append((kind, host, port))

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def starttls(self, **kw):
                log.append(("starttls",))

            def login(self, user, password):
                log.append(("login", user, password))

            def send_message(self, m):
                log.append(("send", m["From"], m["To"], m["Subject"], m.get_content()))
        return Session

    @property
    def SMTP(self):
        return self._session("plain")

    @property
    def SMTP_SSL(self):
        return self._session("ssl")


ENV = {"MAIL_TO": "owner@example.org", "SMTP_HOST": "smtp.example.org",
       "SMTP_USER": "bot@example.org", "SMTP_PASSWORD": "pw"}


def run(env, argv):
    fake, err = FakeSMTP(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = mail.main(argv, env, fake)
    return code, fake.log, err.getvalue()


def main(s):
    with tempfile.TemporaryDirectory() as d:
        body = pathlib.Path(d, "digest.md")
        body.write_text("# Week of 2026-11-09\n\n18 update run(s).\n", encoding="utf-8")
        argv = ["--subject", "Weekly digest: 2026-11-16", str(body)]

        code, log, _ = run(ENV, argv)
        s.eq(code, 0, "a configured account sends")
        s.eq(log[0], ("plain", "smtp.example.org", 587), "port 587 by default, over a plain socket")
        s.eq(log[1], ("starttls",), "which is upgraded before the login")
        s.eq(log[2], ("login", "bot@example.org", "pw"), "the login is the configured one")
        sent = log[3]
        s.eq(sent[1:4], ("bot@example.org", "owner@example.org", "Weekly digest: 2026-11-16"),
             "from the login, to the owner, under the subject given")
        s.check("18 update run(s)." in sent[4], "the body is the file")

        code, log, _ = run({**ENV, "SMTP_PORT": "465", "MAIL_FROM": "Yurarium <bot@example.org>"}, argv)
        s.eq(log[0][0], "ssl", "port 465 speaks TLS from the start")
        s.check(("starttls",) not in log, "and is not upgraded again")
        s.eq(log[-1][1], "Yurarium <bot@example.org>", "a stated sender replaces the login")

        code, log, err = run({**ENV, "MAIL_TO": "", "SMTP_PASSWORD": "  "}, argv)
        s.eq(code, 2, "an unconfigured account fails")
        s.eq(log, [], "and opens no connection")
        s.check("MAIL_TO" in err and "SMTP_PASSWORD" in err, "naming what is missing")
        s.check("bot@example.org" not in err, "and never printing a value")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "mail"))
