# messaging/services.py
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import Context, Template
from django.utils import timezone
from django.db import transaction

from common.models import Communication  # adjust import path
from .models import (
    Campaign,
    CampaignRecipient,
    EmailIntegration,
    RecipientStatus,
    CampaignStatus,
)


def _get_email_connection(integration: EmailIntegration | None):
    if integration is None:
        integration = EmailIntegration.get_default()
    if integration is None:
        raise RuntimeError("No default EmailIntegration configured.")

    if integration.backend_type != "smtp":
        # TODO: implement SendGrid/Mailgun, etc. later.
        # For now, only SMTP is supported.
        raise NotImplementedError("Only SMTP backend is implemented currently.")

    return get_connection(
        host=integration.host,
        port=integration.port,
        username=integration.username,
        password=integration.password,
        use_tls=integration.use_tls,
        use_ssl=integration.use_ssl,
    ), integration.from_email or integration.username


def render_template_for_recipient(template, recipient: CampaignRecipient):
    """
    Build a Django template context from Client/Contact/EventPerson and render HTML + text.
    """
    client = recipient.client
    contact = recipient.contact
    event_person = recipient.event_person

    ctx = {
        "client": client,
        "contact": contact,
        "event_person": event_person,
        "campaign": recipient.campaign,
    }

    # optional conveniences
    if event_person and not contact:
        # You can choose to treat event_person like 'contact' in templates if you want
        ctx.setdefault("contact_name", event_person.full_name)

    context = Context(ctx)

    subject = Template(template.subject).render(context)
    body_text = Template(template.body_text or "").render(context)
    body_html = Template(template.body_html or "").render(context)

    return subject.strip(), body_text, body_html



@transaction.atomic
def send_campaign(campaign: Campaign, limit: int | None = None) -> int:
    """
    Send pending recipients for a campaign. Returns number of emails sent.
    You can call this from:
      - a view (manual 'Send now')
      - a management command
      - Celery beat / cron
    """
    if campaign.status in {CampaignStatus.COMPLETED, CampaignStatus.FAILED}:
        return 0

    if campaign.started_at is None:
        campaign.started_at = timezone.now()
        campaign.status = CampaignStatus.SENDING
        campaign.save(update_fields=["started_at", "status"])

    pending_qs = campaign.recipients.filter(status=RecipientStatus.PENDING)
    if limit:
        pending_qs = pending_qs[:limit]

    pending = list(pending_qs)
    if not pending:
        campaign.status = CampaignStatus.COMPLETED
        campaign.finished_at = timezone.now()
        campaign.save(update_fields=["status", "finished_at"])
        return 0

    connection, from_email = _get_email_connection(campaign.integration)

    sent_count = 0

    for recipient in pending:
        # extra safety: skip if marketing is disabled at person level
        if recipient.contact and hasattr(recipient.contact, "allow_marketing"):
            if not recipient.contact.allow_marketing:
                recipient.status = RecipientStatus.FAILED
                recipient.last_error = "Marketing disabled on contact."
                recipient.save(update_fields=["status", "last_error"])
                continue

        if recipient.event_person and not recipient.event_person.allow_marketing:
            recipient.status = RecipientStatus.FAILED
            recipient.last_error = "Marketing disabled on event person."
            recipient.save(update_fields=["status", "last_error"])
            continue

        try:
            subject, body_text, body_html = render_template_for_recipient(
                campaign.template, recipient
            )

            subject = campaign.subject_override or subject

            message = EmailMultiAlternatives(
                subject=subject,
                body=body_text or body_html,
                from_email=from_email,
                to=[recipient.email],
                connection=connection,
            )
            if body_html:
                message.attach_alternative(body_html, "text/html")

            message.send()

            recipient.status = RecipientStatus.SENT
            recipient.sent_at = timezone.now()
            recipient.last_error = ""
            recipient.save(update_fields=["status", "sent_at", "last_error"])

            # Log to Communication model (if you want)
            Communication.objects.create(
                channel="email",
                subject=subject,
                body=body_html or body_text,
                to_email=recipient.email,
                client=recipient.client,
                contact=recipient.contact,
                related_campaign=campaign,  # if you add such FK
            )

            sent_count += 1

        except Exception as exc:
            recipient.status = RecipientStatus.FAILED
            recipient.last_error = str(exc)[:1000]
            recipient.save(update_fields=["status", "last_error"])

    # If no more pending recipients → mark completed
    if not campaign.recipients.filter(status=RecipientStatus.PENDING).exists():
        campaign.status = CampaignStatus.COMPLETED
        campaign.finished_at = timezone.now()
        campaign.save(update_fields=["status", "finished_at"])

    return sent_count

def send_proposal_email(proposal, template_code="proposal_default"):
    from .models import MessageTemplate
    template = MessageTemplate.objects.get(code=template_code)

    client = proposal.client
    contact = client.primary_contact  # or choose another

    ctx = {
        "client": client,
        "contact": contact,
        "proposal": proposal,
    }

    subject_tpl = Template(template.subject).render(Context(ctx))
    body_html_tpl = Template(template.body_html or "").render(Context(ctx))

    connection, from_email = _get_email_connection(None)
    msg = EmailMultiAlternatives(
        subject=subject_tpl.strip(),
        body=body_html_tpl,
        from_email=from_email,
        to=[contact.email] if contact and contact.email else [],
        connection=connection,
    )
    if body_html_tpl:
        msg.attach_alternative(body_html_tpl, "text/html")
    msg.send()
