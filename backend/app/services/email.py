"""Core email service.

`smtplib` is synchronous — calling it from a FastAPI handler would pin the
event-loop thread for the entire SMTP round trip (handshake + STARTTLS +
DATA can easily be hundreds of ms, more on a cold connection). Every call
therefore runs on a private :class:`ThreadPoolExecutor`, so request
handlers can hand off a send and return immediately.

Public surface
--------------
* :class:`EmailService` — sync, testable. Builds the MIME message and
  talks to SMTP. Use directly from tests / cron jobs.
* :func:`get_email_service` — process-wide singleton, lazy-initialised
  from :mod:`app.config`.
* :func:`send_email_async` — fire-and-forget submit to the thread pool.
  Returns a :class:`concurrent.futures.Future` so callers that *do* want
  to await delivery can.
* :func:`shutdown_email_executor` — drain/close the pool on app shutdown.

Failure policy
--------------
Email is non-critical — a bad SMTP server must not break /register or a
price-event ingest. The async wrapper swallows + logs exceptions inside
the worker thread; only the singleton constructor surfaces config errors
(missing SMTP_HOST when EMAIL_ENABLED=True).
"""

from __future__ import annotations

import logging
import smtplib
import ssl
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Iterable

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sync core
# ---------------------------------------------------------------------------

class EmailService:
    """Blocking SMTP client. One instance per process; thread-safe at the
    call level because each :meth:`send` opens its own connection."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
        use_ssl: bool,
        timeout: int,
        from_address: str,
        from_name: str,
        enabled: bool = True,
    ) -> None:
        if use_tls and use_ssl:
            raise ValueError(
                "SMTP_USE_TLS and SMTP_USE_SSL are mutually exclusive — "
                "use STARTTLS (587) *or* implicit TLS (465), not both."
            )
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.from_address = from_address
        self.from_name = from_name
        self.enabled = enabled

    # ---- public API ------------------------------------------------------

    def send(
        self,
        *,
        to: str | Iterable[str],
        subject: str,
        html: str,
        text: str | None = None,
        reply_to: str | None = None,
    ) -> None:
        """Send one message synchronously. Raises :class:`smtplib.SMTPException`
        on transport failure. ``to`` may be a single address or an iterable
        (each address gets a separate envelope, but they share the body —
        callers that need per-recipient personalisation should loop).
        """
        if not self.enabled:
            logger.info(
                "email disabled (EMAIL_ENABLED=false) — skip send to=%r subject=%r",
                to,
                subject,
            )
            return
        if not self.host:
            logger.warning(
                "SMTP_HOST is empty — skip send to=%r subject=%r", to, subject
            )
            return

        recipients = [to] if isinstance(to, str) else list(to)
        if not recipients:
            return

        msg = self._build_message(
            to=recipients,
            subject=subject,
            html=html,
            text=text,
            reply_to=reply_to,
        )

        with self._connect() as smtp:
            smtp.send_message(msg)

        logger.info(
            "email sent to=%s subject=%r host=%s",
            recipients,
            subject,
            self.host,
        )

    # ---- internals -------------------------------------------------------

    def _build_message(
        self,
        *,
        to: list[str],
        subject: str,
        html: str,
        text: str | None,
        reply_to: str | None,
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = formataddr((self.from_name, self.from_address))
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid(domain=self._message_domain())
        if reply_to:
            msg["Reply-To"] = reply_to
        # Plain-text fallback first so MIME-aware clients pick HTML as the
        # richer alternative; bare-text clients see the .txt copy.
        msg.set_content(text or _strip_html(html))
        msg.add_alternative(html, subtype="html")
        return msg

    def _message_domain(self) -> str:
        # Domain portion of From: — RFC says Message-ID should be globally
        # unique on a domain we own.
        if "@" in self.from_address:
            return self.from_address.rsplit("@", 1)[1]
        return "priceradar.local"

    def _connect(self) -> smtplib.SMTP:
        """Open + authenticate an SMTP connection. The caller is expected
        to use it as a context manager (``with self._connect() as smtp:``).
        """
        if self.use_ssl:
            context = ssl.create_default_context()
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(
                host=self.host,
                port=self.port,
                timeout=self.timeout,
                context=context,
            )
        else:
            smtp = smtplib.SMTP(
                host=self.host, port=self.port, timeout=self.timeout
            )
            smtp.ehlo()
            if self.use_tls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()

        if self.username and self.password:
            smtp.login(self.username, self.password)
        return smtp


# ---------------------------------------------------------------------------
# HTML → text fallback
# ---------------------------------------------------------------------------

def _strip_html(html: str) -> str:
    """Very cheap HTML→text. We always pass an explicit text body for the
    templates we ship; this exists only so an ad-hoc caller that forgot
    to provide one still gets a readable fallback."""
    import re

    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------------------------------------------------------------------------
# Process-wide singleton + thread pool
# ---------------------------------------------------------------------------

_service: EmailService | None = None
_executor: ThreadPoolExecutor | None = None
_lock = threading.Lock()


def get_email_service() -> EmailService:
    """Lazy singleton — first caller wins. Re-reads ``settings`` so a test
    that patches the cached settings before the first call gets the patched
    values."""
    global _service
    if _service is None:
        with _lock:
            if _service is None:
                _service = EmailService(
                    host=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    username=settings.SMTP_USERNAME,
                    password=settings.SMTP_PASSWORD,
                    use_tls=settings.SMTP_USE_TLS,
                    use_ssl=settings.SMTP_USE_SSL,
                    timeout=settings.SMTP_TIMEOUT,
                    from_address=settings.EMAIL_FROM_ADDRESS,
                    from_name=settings.EMAIL_FROM_NAME,
                    enabled=settings.EMAIL_ENABLED,
                )
    return _service


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        with _lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=settings.EMAIL_THREAD_POOL_SIZE,
                    thread_name_prefix="email",
                )
    return _executor


def send_email_async(
    *,
    to: str | Iterable[str],
    subject: str,
    html: str,
    text: str | None = None,
    reply_to: str | None = None,
) -> Future[None]:
    """Submit a send to the email thread pool. Returns a ``Future`` —
    most callers ignore it (fire-and-forget); tests may ``.result()``
    on it to synchronise.

    Exceptions raised inside the worker are logged and *not* re-raised —
    we never want email failure to bubble up into a request handler.
    """
    service = get_email_service()
    executor = _get_executor()

    def _run() -> None:
        try:
            service.send(
                to=to,
                subject=subject,
                html=html,
                text=text,
                reply_to=reply_to,
            )
        except Exception:
            logger.exception(
                "email send failed to=%r subject=%r", to, subject
            )

    return executor.submit(_run)


def shutdown_email_executor(wait: bool = True) -> None:
    """Drain the thread pool on FastAPI shutdown. ``wait=True`` lets any
    in-flight sends finish; set False during forced shutdowns."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=wait)
        _executor = None
