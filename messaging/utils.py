# messaging/utils.py

from __future__ import annotations

from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from django.conf import settings
from django.core.files.base import ContentFile
from django.template import Context, Template
from django.utils import timezone

from .models import EmailTemplate, EmailSendLog


class EmailSendError(Exception):
    pass


@dataclass
class SendResult:
    ok: bool
    message_id: str = ""
    error: str = ""
    skipped: bool = False


def email_sending_enabled() -> bool:
    return bool(getattr(settings, "EMAIL_SENDING_ENABLED", False))


def normalize_emails(emails: Union[str, Sequence[str], None]) -> list[str]:
    if not emails:
        return []

    if isinstance(emails, str):
        emails = [emails]

    return [email.strip() for email in emails if email and email.strip()]


def get_ses_client():
    region = getattr(settings, "AWS_REGION", None) or getattr(settings, "AWS_DEFAULT_REGION", None)

    if not region:
        raise EmailSendError("AWS region is not configured. Add AWS_REGION in settings/.env.")

    access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
    secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)

    kwargs = {"region_name": region}

    if access_key and secret_key:
        kwargs.update(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    return boto3.client("ses", **kwargs)


def get_active_template(template_type: str) -> EmailTemplate:
    template = (
        EmailTemplate.objects
        .filter(type=template_type, is_active=True)
        .prefetch_related("attachments")
        .first()
    )

    if not template:
        raise EmailSendError(f"No active email template found for '{template_type}'.")

    return template


def render_template_string(template_str: str, context: Dict[str, Any]) -> str:
    if not template_str:
        return ""

    return Template(template_str).render(Context(context))


def render_email_from_template(
    template: EmailTemplate,
    context: Dict[str, Any],
) -> Tuple[str, str, str]:
    context = dict(context or {})
    context.setdefault("now", timezone.now())
    context.setdefault("today", timezone.localdate())

    subject = render_template_string(template.subject, context).strip()
    body_html = render_template_string(template.body_html, context)
    body_text = render_template_string(template.body_text, context)

    if not subject:
        raise EmailSendError(f"Template '{template.slug}' produced an empty subject.")

    if not body_html and not body_text:
        raise EmailSendError(f"Template '{template.slug}' produced an empty body.")

    return subject, body_html, body_text


def send_email_ses(
    *,
    to_emails: Union[str, Sequence[str]],
    subject: str,
    body_html: str = "",
    body_text: str = "",
    from_email: Optional[str] = None,
    reply_to: Optional[Union[str, Sequence[str]]] = None,
    cc: Optional[Union[str, Sequence[str]]] = None,
    bcc: Optional[Union[str, Sequence[str]]] = None,
    charset: str = "UTF-8",
) -> SendResult:
    if not email_sending_enabled():
        return SendResult(
            ok=False,
            skipped=True,
            error="Email sending is disabled in settings.",
        )

    to_list = normalize_emails(to_emails)
    cc_list = normalize_emails(cc)
    bcc_list = normalize_emails(bcc)
    reply_to_list = normalize_emails(reply_to)

    if not to_list:
        return SendResult(ok=False, error="No recipient email provided.")

    sender = (
        from_email
        or getattr(settings, "EMAIL_DEFAULT_FROM", "")
        or getattr(settings, "AWS_SES_SENDER", "")
    ).strip()

    if not sender:
        return SendResult(ok=False, error="Sender email is not configured.")

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

    try:
        client = get_ses_client()

        kwargs = {
            "Source": sender,
            "Destination": destination,
            "Message": message,
        }

        if reply_to_list:
            kwargs["ReplyToAddresses"] = reply_to_list

        response = client.send_email(**kwargs)

        return SendResult(
            ok=True,
            message_id=response.get("MessageId", ""),
        )

    except (ClientError, BotoCoreError) as exc:
        return SendResult(ok=False, error=str(exc))


def send_raw_email_ses(
    *,
    to_emails: Union[str, Sequence[str]],
    subject: str,
    body_html: str = "",
    body_text: str = "",
    attachments: Optional[list[dict]] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[Union[str, Sequence[str]]] = None,
) -> SendResult:
    if not email_sending_enabled():
        return SendResult(
            ok=False,
            skipped=True,
            error="Email sending is disabled in settings.",
        )

    to_list = normalize_emails(to_emails)
    reply_to_list = normalize_emails(reply_to)

    if not to_list:
        return SendResult(ok=False, error="No recipient email provided.")

    sender = (
        from_email
        or getattr(settings, "EMAIL_DEFAULT_FROM", "")
        or getattr(settings, "AWS_SES_SENDER", "")
    ).strip()

    if not sender:
        return SendResult(ok=False, error="Sender email is not configured.")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to_list)

    if reply_to_list:
        msg["Reply-To"] = ", ".join(reply_to_list)

    alternative = MIMEMultipart("alternative")

    if body_text:
        alternative.attach(MIMEText(body_text, "plain", "utf-8"))

    if body_html:
        alternative.attach(MIMEText(body_html, "html", "utf-8"))

    msg.attach(alternative)

    for attachment in attachments or []:
        filename = attachment.get("filename")
        content = attachment.get("content")
        content_type = attachment.get("content_type") or "application/octet-stream"

        if not filename or content is None:
            continue

        part = MIMEApplication(content)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        part.add_header("Content-Type", content_type)
        msg.attach(part)

    try:
        client = get_ses_client()

        response = client.send_raw_email(
            Source=sender,
            Destinations=to_list,
            RawMessage={"Data": msg.as_string()},
        )

        return SendResult(
            ok=True,
            message_id=response.get("MessageId", ""),
        )

    except (ClientError, BotoCoreError) as exc:
        return SendResult(ok=False, error=str(exc))


def build_template_attachments(template: EmailTemplate) -> list[dict]:
    attachments = []

    for item in template.attachments.filter(is_active=True):
        if not item.file:
            continue

        filename = item.display_name or item.file.name.split("/")[-1]

        item.file.open("rb")
        content = item.file.read()
        item.file.close()

        attachments.append({
            "filename": filename,
            "content": content,
            "content_type": "application/octet-stream",
        })

    return attachments


def send_templated_email(
    *,
    template_type: str,
    to_emails: Union[str, Sequence[str]],
    context: Dict[str, Any],
    related_object=None,
    generated_pdf: Optional[dict] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[Union[str, Sequence[str]]] = None,
) -> SendResult:
    """
    Main function for proposal/contract/invoice/payment/anniversary/campaign.

    generated_pdf example:
    {
        "filename": "invoice-1001.pdf",
        "content": pdf_bytes,
        "content_type": "application/pdf",
    }
    """

    log = EmailSendLog(
        template_type=template_type,
        to_email=", ".join(normalize_emails(to_emails)),
        related_model=related_object.__class__.__name__ if related_object else "",
        related_object_id=getattr(related_object, "pk", None),
    )

    try:
        template = get_active_template(template_type)
        log.template = template

        subject, body_html, body_text = render_email_from_template(template, context)
        log.subject = subject
        log.save()

        attachments = build_template_attachments(template)

        if template.attach_generated_pdf and generated_pdf:
            attachments.append(generated_pdf)

        if attachments:
            result = send_raw_email_ses(
                to_emails=to_emails,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                attachments=attachments,
                from_email=from_email,
                reply_to=reply_to,
            )
        else:
            result = send_email_ses(
                to_emails=to_emails,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                from_email=from_email,
                reply_to=reply_to,
            )

        if result.ok:
            log.mark_sent(result.message_id)
        else:
            if result.skipped:
                log.status = EmailSendLog.Status.SKIPPED
                log.error_message = result.error
                log.save(update_fields=["status", "error_message"])
            else:
                log.mark_failed(result.error)

        return result

    except Exception as exc:
        log.status = EmailSendLog.Status.FAILED
        log.error_message = str(exc)
        log.save()
        return SendResult(ok=False, error=str(exc))