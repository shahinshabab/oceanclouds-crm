# messaging/utils.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple, Union

from django.conf import settings
from django.template import Context, Template
from django.utils import timezone
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .models import EmailTemplate
import re

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

def parse_custom_list(raw: str):
    """
    Accepts lines like:
      John Doe, john@x.com
      john@x.com
      "John, Jr", john@x.com   (works best if user avoids extra commas)
    Returns list of dicts: [{"name": "...", "email": "..."}]
    """
    results = []
    if not raw:
        return results

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        # if line contains an email anywhere, extract it
        m = EMAIL_RE.search(line)
        if not m:
            continue

        email = m.group(0).strip().lower()

        # try name part before email, removing trailing commas
        name_part = line[: m.start()].strip().strip(",").strip()
        name = name_part or ""

        results.append({"name": name, "email": email})

    # de-duplicate by email (keep first)
    seen = set()
    unique = []
    for r in results:
        if r["email"] in seen:
            continue
        seen.add(r["email"])
        unique.append(r)
    return unique

# -----------------------------------------------------------------------------
# Result / Exceptions
# -----------------------------------------------------------------------------

class EmailSendError(Exception):
    """Raised when SES sending fails or template lookup/render fails."""


@dataclass
class SendResult:
    ok: bool
    message_id: str = ""
    error: str = ""


# -----------------------------------------------------------------------------
# SES client
# -----------------------------------------------------------------------------

def get_ses_client():
    """
    Create a boto3 SES client from Django settings.
    You can swap to STS roles later without touching call sites.
    """
    region = getattr(settings, "AWS_REGION", None) or getattr(settings, "AWS_DEFAULT_REGION", None)
    if not region:
        raise EmailSendError("AWS region not configured (AWS_REGION).")

    access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
    secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)

    # If keys are not provided, boto3 will use env/instance role automatically.
    kwargs = {"region_name": region}
    if access_key and secret_key:
        kwargs.update(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    return boto3.client("ses", **kwargs)


# -----------------------------------------------------------------------------
# Template lookup
# -----------------------------------------------------------------------------

def get_default_template(template_type: str) -> EmailTemplate:
    """
    Fetch default active template for a given type.
    Falls back to any active template of that type if default is not set.
    """
    qs = EmailTemplate.objects.filter(is_active=True, type=template_type)

    tpl = qs.filter(is_default_for_type=True).first()
    if tpl:
        return tpl

    tpl = qs.order_by("name").first()
    if tpl:
        return tpl

    raise EmailSendError(f"No active template found for type='{template_type}'.")


def get_template_by_slug(slug: str) -> EmailTemplate:
    tpl = EmailTemplate.objects.filter(is_active=True, slug=slug).first()
    if not tpl:
        raise EmailSendError(f"No active template found for slug='{slug}'.")
    return tpl


# -----------------------------------------------------------------------------
# Rendering
# -----------------------------------------------------------------------------

def render_template_string(template_str: str, context: Dict[str, Any]) -> str:
    """
    Render a string using Django's template engine.
    Your EmailTemplate body can contain: {{ client.name }}, {{ deal.title }}, etc.
    """
    if not template_str:
        return ""
    # Use Template/Context to render model-stored templates
    return Template(template_str).render(Context(context))


def render_email_from_template(
    tpl: EmailTemplate,
    context: Dict[str, Any],
) -> Tuple[str, str, str]:
    """
    Returns (subject, html, text).
    """
    subject = render_template_string(tpl.subject or "", context).strip()
    html = render_template_string(tpl.body_html or "", context)
    text = render_template_string(tpl.body_text or "", context)

    if not subject:
        raise EmailSendError(f"Template '{tpl.slug}' produced empty subject.")
    if not html and not text:
        raise EmailSendError(f"Template '{tpl.slug}' produced empty body (html/text).")

    # If text is empty, we still send HTML-only; SES supports that.
    return subject, html, text


# -----------------------------------------------------------------------------
# Sending
# -----------------------------------------------------------------------------

def normalize_emails(emails: Union[str, Sequence[str], None]) -> list[str]:
    if not emails:
        return []
    if isinstance(emails, str):
        emails = [emails]
    return [e.strip() for e in emails if e and e.strip()]


def send_email_ses(
    to_emails: Union[str, Sequence[str]],
    subject: str,
    body_html: str = "",
    body_text: str = "",
    *,
    from_email: Optional[str] = None,
    reply_to: Optional[Union[str, Sequence[str]]] = None,
    cc: Optional[Union[str, Sequence[str]]] = None,
    bcc: Optional[Union[str, Sequence[str]]] = None,
    charset: str = "UTF-8",
) -> SendResult:
    """
    Low-level SES sender. Reusable anywhere.
    """
    to_list = normalize_emails(to_emails)
    cc_list = normalize_emails(cc)
    bcc_list = normalize_emails(bcc)
    reply_to_list = normalize_emails(reply_to)

    if not to_list:
        return SendResult(ok=False, error="No recipients provided.")

    sender = (from_email or getattr(settings, "AWS_SES_SENDER", "")).strip()
    if not sender:
        return SendResult(ok=False, error="Sender not configured (AWS_SES_SENDER).")

    destination = {"ToAddresses": to_list}
    if cc_list:
        destination["CcAddresses"] = cc_list
    if bcc_list:
        destination["BccAddresses"] = bcc_list

    message = {
        "Subject": {"Data": subject, "Charset": charset},
        "Body": {},
    }
    if body_text:
        message["Body"]["Text"] = {"Data": body_text, "Charset": charset}
    if body_html:
        message["Body"]["Html"] = {"Data": body_html, "Charset": charset}

    client = get_ses_client()

    try:
        kwargs = {
            "Source": sender,
            "Destination": destination,
            "Message": message,
        }

        # Only include ReplyToAddresses if you actually have reply-to emails
        if reply_to_list:
            kwargs["ReplyToAddresses"] = reply_to_list

        resp = client.send_email(**kwargs)
        return SendResult(ok=True, message_id=resp.get("MessageId", ""))
    except (ClientError, BotoCoreError) as e:
        return SendResult(ok=False, error=str(e))



# -----------------------------------------------------------------------------
# High-level helper (template-driven)
# -----------------------------------------------------------------------------

def send_templated_email(
    *,
    template_type: Optional[str] = None,
    template_slug: Optional[str] = None,
    to_emails: Union[str, Sequence[str]],
    context: Dict[str, Any],
    from_email: Optional[str] = None,
    reply_to: Optional[Union[str, Sequence[str]]] = None,
    cc: Optional[Union[str, Sequence[str]]] = None,
    bcc: Optional[Union[str, Sequence[str]]] = None,
) -> SendResult:
    """
    High-level function used by other apps.
    - Pick a template (by slug OR default by type)
    - Render it with context
    - Send through SES
    """
    if not template_slug and not template_type:
        raise EmailSendError("Provide template_slug or template_type.")

    if template_slug:
        tpl = get_template_by_slug(template_slug)
    else:
        tpl = get_default_template(template_type)

    # Helpful default context values
    context = dict(context or {})
    context.setdefault("now", timezone.now())
    context.setdefault("today", timezone.localdate())

    subject, html, text = render_email_from_template(tpl, context)

    return send_email_ses(
        to_emails=to_emails,
        subject=subject,
        body_html=html,
        body_text=text,
        from_email=from_email,
        reply_to=reply_to,
        cc=cc,
        bcc=bcc,
    )
