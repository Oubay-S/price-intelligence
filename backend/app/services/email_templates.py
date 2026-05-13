"""HTML email templates.

Each builder returns ``(subject, html_body, text_body)``. The plain-text
copy mirrors the HTML so clients that strip HTML still get a usable
message (and so spam filters don't flag the message as HTML-only).

Templates are intentionally inline-styled and self-contained — no external
CSS, no remote images. Gmail/Outlook strip <style> blocks and block
external resources by default, so any layout we want preserved has to
live on the element itself.
"""

from __future__ import annotations

from html import escape


# ---------------------------------------------------------------------------
# Shared chrome — header banner + footer. Kept here, not duplicated across
# every builder, so a re-brand only touches one place.
# ---------------------------------------------------------------------------

_BRAND_COLOR = "#0F766E"      # teal-700
_BRAND_ACCENT = "#14B8A6"     # teal-500
_TEXT_COLOR = "#0F172A"       # slate-900
_MUTED_COLOR = "#64748B"      # slate-500
_BG_COLOR = "#F8FAFC"         # slate-50
_CARD_COLOR = "#FFFFFF"


def _wrap(content_html: str, *, preheader: str = "") -> str:
    """Wrap an inner content fragment in the shared layout shell."""
    preheader_html = (
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;'
        f'color:transparent;">{escape(preheader)}</div>'
        if preheader
        else ""
    )
    return f"""\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>PriceRadar</title>
  </head>
  <body style="margin:0;padding:0;background:{_BG_COLOR};
               font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',
               Roboto,Helvetica,Arial,sans-serif;color:{_TEXT_COLOR};">
    {preheader_html}
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:{_BG_COLOR};padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="560" cellpadding="0" cellspacing="0"
                 style="max-width:560px;width:100%;background:{_CARD_COLOR};
                        border-radius:12px;overflow:hidden;
                        box-shadow:0 1px 3px rgba(15,23,42,0.08);">
            <tr>
              <td style="background:{_BRAND_COLOR};padding:20px 28px;">
                <div style="color:#fff;font-size:18px;font-weight:700;
                            letter-spacing:0.2px;">PriceRadar</div>
                <div style="color:#A7F3D0;font-size:12px;margin-top:2px;">
                  Sports-nutrition price intelligence
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:28px;font-size:15px;line-height:1.55;">
                {content_html}
              </td>
            </tr>
            <tr>
              <td style="padding:20px 28px;background:#F1F5F9;
                         color:{_MUTED_COLOR};font-size:12px;
                         line-height:1.5;text-align:center;">
                You're receiving this because you signed up to PriceRadar.
                <br>If this wasn't you, you can safely ignore this email.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _button(label: str, href: str) -> str:
    return (
        f'<a href="{escape(href, quote=True)}" '
        f'style="display:inline-block;background:{_BRAND_ACCENT};color:#fff;'
        f'text-decoration:none;font-weight:600;padding:12px 22px;'
        f'border-radius:8px;font-size:14px;">{escape(label)}</a>'
    )


def _fallback_link(href: str) -> str:
    return (
        f'<p style="color:{_MUTED_COLOR};font-size:13px;margin:20px 0 0;">'
        f'If the button doesn\'t work, paste this link into your browser:<br>'
        f'<a href="{escape(href, quote=True)}" '
        f'style="color:{_BRAND_COLOR};word-break:break-all;">'
        f'{escape(href)}</a></p>'
    )


# ---------------------------------------------------------------------------
# 1) Email verification
# ---------------------------------------------------------------------------

def build_verification_email(
    *, full_name: str | None, verification_url: str, ttl_hours: int
) -> tuple[str, str, str]:
    greeting = f"Hi {escape(full_name)}," if full_name else "Hi,"
    subject = "Verify your PriceRadar email address"

    inner = f"""\
      <h1 style="margin:0 0 16px;font-size:20px;color:{_TEXT_COLOR};">
        Confirm your email
      </h1>
      <p style="margin:0 0 16px;">{greeting}</p>
      <p style="margin:0 0 20px;">
        Thanks for signing up. Click the button below to verify your email
        address and activate price alerts on your watchlist.
      </p>
      <p style="margin:0 0 24px;">{_button("Verify email", verification_url)}</p>
      <p style="margin:0;color:{_MUTED_COLOR};font-size:13px;">
        This link expires in {ttl_hours} hour{"s" if ttl_hours != 1 else ""}.
      </p>
      {_fallback_link(verification_url)}
    """
    html = _wrap(inner, preheader="Confirm your email to activate price alerts.")
    text = (
        f"{greeting.replace('<', '').replace('>', '')}\n\n"
        "Thanks for signing up to PriceRadar. Open the link below to verify "
        "your email and activate price alerts on your watchlist:\n\n"
        f"{verification_url}\n\n"
        f"This link expires in {ttl_hours} hour"
        f"{'s' if ttl_hours != 1 else ''}.\n\n"
        "If you didn't sign up, you can ignore this email.\n"
        "— PriceRadar"
    )
    return subject, html, text


# ---------------------------------------------------------------------------
# 2) Password reset
# ---------------------------------------------------------------------------

def build_password_reset_email(
    *, full_name: str | None, reset_url: str, ttl_hours: int
) -> tuple[str, str, str]:
    greeting = f"Hi {escape(full_name)}," if full_name else "Hi,"
    subject = "Reset your PriceRadar password"

    inner = f"""\
      <h1 style="margin:0 0 16px;font-size:20px;color:{_TEXT_COLOR};">
        Reset your password
      </h1>
      <p style="margin:0 0 16px;">{greeting}</p>
      <p style="margin:0 0 20px;">
        We received a request to reset the password for your PriceRadar
        account. Click the button below to choose a new password.
      </p>
      <p style="margin:0 0 24px;">{_button("Reset password", reset_url)}</p>
      <p style="margin:0;color:{_MUTED_COLOR};font-size:13px;">
        This link expires in {ttl_hours} hour{"s" if ttl_hours != 1 else ""}
        and can only be used once.
      </p>
      <p style="margin:16px 0 0;color:{_MUTED_COLOR};font-size:13px;">
        If you didn't request a password reset, you can safely ignore this
        email — your password will not change.
      </p>
      {_fallback_link(reset_url)}
    """
    html = _wrap(inner, preheader="Reset your PriceRadar password.")
    text = (
        f"{greeting.replace('<', '').replace('>', '')}\n\n"
        "We received a request to reset your PriceRadar password. Open the "
        "link below to choose a new one:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in {ttl_hours} hour"
        f"{'s' if ttl_hours != 1 else ''} and can only be used once.\n\n"
        "If you didn't request a reset, ignore this email.\n"
        "— PriceRadar"
    )
    return subject, html, text


# ---------------------------------------------------------------------------
# 3) Price-drop alert (sent when user is offline; WebSocket handles online)
# ---------------------------------------------------------------------------

def _format_price(amount: float, currency: str = "USD") -> str:
    return f"{currency} {amount:,.2f}"


def build_price_drop_email(
    *,
    full_name: str | None,
    product_title: str,
    site: str,
    listing_url: str,
    product_image_url: str | None,
    price_before: float,
    price_after: float,
    drop_pct: float,
    currency: str = "USD",
    watchlist_url: str | None = None,
) -> tuple[str, str, str]:
    greeting = f"Hi {escape(full_name)}," if full_name else "Hi,"
    subject = (
        f"Price drop: {product_title} is now "
        f"{_format_price(price_after, currency)} (-{drop_pct:.1f}%)"
    )

    image_html = (
        f'<tr><td align="center" style="padding:0 0 20px;">'
        f'<img src="{escape(product_image_url, quote=True)}" '
        f'alt="" width="160" '
        f'style="max-width:160px;height:auto;border-radius:8px;border:0;"></td></tr>'
        if product_image_url
        else ""
    )

    cta_html = _button("View on " + site, listing_url)
    secondary_cta = (
        f'<p style="margin:12px 0 0;">'
        f'<a href="{escape(watchlist_url, quote=True)}" '
        f'style="color:{_BRAND_COLOR};text-decoration:none;font-size:13px;">'
        f'Manage your watchlist →</a></p>'
        if watchlist_url
        else ""
    )

    inner = f"""\
      <h1 style="margin:0 0 16px;font-size:20px;color:{_TEXT_COLOR};">
        Price drop on your watchlist
      </h1>
      <p style="margin:0 0 20px;">{greeting}</p>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="border:1px solid #E2E8F0;border-radius:10px;
                    padding:20px;margin-bottom:20px;">
        {image_html}
        <tr>
          <td style="padding:0 0 12px;font-size:16px;font-weight:600;">
            {escape(product_title)}
          </td>
        </tr>
        <tr>
          <td style="padding:0 0 8px;color:{_MUTED_COLOR};font-size:13px;">
            on {escape(site)}
          </td>
        </tr>
        <tr>
          <td style="padding:8px 0 4px;">
            <span style="text-decoration:line-through;color:{_MUTED_COLOR};
                         font-size:14px;margin-right:8px;">
              {_format_price(price_before, currency)}
            </span>
            <span style="color:{_BRAND_COLOR};font-size:20px;font-weight:700;">
              {_format_price(price_after, currency)}
            </span>
          </td>
        </tr>
        <tr>
          <td style="padding:0 0 16px;">
            <span style="display:inline-block;background:#D1FAE5;
                         color:#065F46;font-size:12px;font-weight:600;
                         padding:3px 8px;border-radius:999px;">
              -{drop_pct:.1f}%
            </span>
          </td>
        </tr>
        <tr><td>{cta_html}</td></tr>
      </table>

      <p style="margin:0;color:{_MUTED_COLOR};font-size:13px;">
        Prices and stock change fast — we recommend acting quickly if this
        hits your target.
      </p>
      {secondary_cta}
    """
    html = _wrap(
        inner,
        preheader=f"{product_title} is now {_format_price(price_after, currency)}",
    )
    text = (
        f"{greeting.replace('<', '').replace('>', '')}\n\n"
        f"Price drop on your watchlist:\n\n"
        f"{product_title}\n"
        f"On: {site}\n"
        f"Was: {_format_price(price_before, currency)}\n"
        f"Now: {_format_price(price_after, currency)} (-{drop_pct:.1f}%)\n\n"
        f"View listing: {listing_url}\n"
    )
    if watchlist_url:
        text += f"\nManage your watchlist: {watchlist_url}\n"
    text += "\n— PriceRadar"
    return subject, html, text
