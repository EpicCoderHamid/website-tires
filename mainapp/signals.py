# mainapp/signals.py
import logging
from functools import partial

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction

from django.template.loader import render_to_string, TemplateDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .models import Order

logger = logging.getLogger(__name__)

def send_email(subject, to_email, html_template, context, text_template=None, from_email=None):
    """
    Build and send a multipart email (text + html). Logs detailed errors but
    does not raise exceptions to avoid breaking the DB save flow.
    - to_email can be a string or a list/tuple of addresses.
    """
    from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tireshop.local')

    # Normalize recipients to a list
    if isinstance(to_email, (list, tuple)):
        recipients = list(to_email)
    elif isinstance(to_email, str):
        # Allow comma-separated string for multiple recipients
        recipients = [addr.strip() for addr in to_email.split(",") if addr.strip()]
    else:
        logger.error("Invalid to_email type: %r", type(to_email))
        return

    # Render text and html bodies; if template missing, log and continue
    text_body = ''
    if text_template:
        try:
            text_body = render_to_string(text_template, context)
        except TemplateDoesNotExist:
            logger.exception("Text template not found: %s", text_template)
            text_body = ''
        except Exception:
            logger.exception("Error rendering text template %s", text_template)

    try:
        html_body = render_to_string(html_template, context)
    except TemplateDoesNotExist:
        logger.exception("HTML template not found: %s", html_template)
        html_body = ''
    except Exception:
        logger.exception("Error rendering HTML template %s", html_template)
        html_body = ''

    # Create and send the email
    try:
        msg = EmailMultiAlternatives(subject, text_body, from_email, recipients)
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info("Email sent: subject=%r to=%s", subject, recipients)
    except Exception as exc:
        logger.exception("Failed to send email (subject=%r to=%s): %s", subject, recipients, exc)
        # Do not raise to avoid interrupting the save/post_save flow

@receiver(pre_save, sender=Order)
def cache_previous_status(sender, instance, **kwargs):
    """
    Save previous status on the instance before saving (so post_save can detect change).
    """
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        previous = Order.objects.get(pk=instance.pk)
        instance._previous_status = previous.status
    except Order.DoesNotExist:
        instance._previous_status = None
    except Exception:
        logger.exception("Error caching previous status for Order pk=%s", instance.pk)
        instance._previous_status = None

@receiver(post_save, sender=Order)
def order_created_or_status_changed(sender, instance, created, **kwargs):
    """
    Send confirmation emails on creation and status-change notifications on updates.
    Admin notification will be sent if ORDER_NOTIFICATION_EMAIL is set in settings.
    Emails are scheduled to run after the DB transaction commits to avoid 'database is locked'.
    """
    context = {
        'order': instance,
        'order_id': instance.order_number or instance.pk,
        'order_total': getattr(instance, 'total_amount', None),
        'customer_name': instance.customer_name or '',
        'current_status': instance.status,
        'previous_status': getattr(instance, '_previous_status', None),
    }

    # New order -> send confirmation email to customer (and optionally admin)
    if created:
        if instance.customer_email:
            subject = f"Order Confirmation — {context['order_id']}"
            try:
                task = partial(
                    send_email,
                    subject,
                    instance.customer_email,
                    'tires/order_confirmation.html',
                    context,
                    'tires/order_confirmation.txt'
                )
                transaction.on_commit(task)
            except Exception:
                logger.exception("Unexpected error scheduling new-order email to customer %s", instance.customer_email)

        # Optional admin notification if configured (can be comma-separated or a list)
        admin_email = getattr(settings, 'ORDER_NOTIFICATION_EMAIL', None)
        if admin_email:
            try:
                task_admin = partial(
                    send_email,
                    f"New order {context['order_id']}",
                    admin_email,
                    'tires/order_confirmation.html',
                    context,
                    'tires/order_confirmation.txt'
                )
                transaction.on_commit(task_admin)
            except Exception:
                logger.exception("Unexpected error scheduling new-order email to admin %s", admin_email)
        return

    # Status changed -> send status update to customer
    prev = getattr(instance, '_previous_status', None)
    curr = instance.status
    if prev != curr:
        if instance.customer_email:
            subject = f"Order {context['order_id']} Status Updated: {curr}"
            try:
                task_status = partial(
                    send_email,
                    subject,
                    instance.customer_email,
                    'tires/order_status_change.html',
                    context,
                    'tires/order_status_change.txt'
                )
                transaction.on_commit(task_status)
            except Exception:
                logger.exception("Unexpected error scheduling order-status email for order %s to %s", context['order_id'], instance.customer_email)
