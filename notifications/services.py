import logging
from datetime import date, timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from inventory.models import MedicineBatch
from notifications.models import ExpiryNotification

logger = logging.getLogger(__name__)
User = get_user_model()


class ExpiryAlertService:
    """
    Automated service that scans medicine batches, detects expiration stages,
    generates notification records, and dispatches email alerts to authorized staff
    while strictly preventing duplicate alerts within the same category period.
    """

    @classmethod
    def get_recipient_emails(cls):
        """Fetch emails of all active staff and administrators, plus fallback configured email."""
        emails = set()
        active_users = User.objects.filter(is_active=True).exclude(email='').values_list('email', flat=True)
        emails.update(active_users)

        fallback = getattr(settings, 'ADMIN_ALERT_EMAIL', None)
        if fallback:
            emails.add(fallback)

        if not emails:
            emails.add('pharmacy-staff@example.com')
        return list(emails)

    @classmethod
    def run_expiry_check(cls, send_emails=True):
        """
        Executes complete scan of all batches with available stock.
        Returns a dictionary summarizing detected and processed alerts.
        """
        today = date.today()
        # Find all batches with remaining stock
        batches = MedicineBatch.objects.filter(
            available_quantity__gt=0
        ).select_related('medicine', 'supplier', 'medicine__category')

        summary = {
            'scanned_batches': batches.count(),
            'already_expired': 0,
            'critical_7': 0,
            'urgent_15': 0,
            'warning_30': 0,
            'new_notifications_created': 0,
            'emails_sent': 0,
            'duplicates_skipped': 0,
            'details': []
        }

        recipients = cls.get_recipient_emails()

        for batch in batches:
            days = batch.days_to_expiry
            category = None
            category_label = ""

            if days < 0:
                category = ExpiryNotification.AlertCategory.EXPIRED
                category_label = f"EXPIRED ({abs(days)} days ago)"
                summary['already_expired'] += 1
            elif days <= 7:
                category = ExpiryNotification.AlertCategory.CRITICAL_7
                category_label = f"CRITICAL: Expiring in {days} days (<= 7 Days)"
                summary['critical_7'] += 1
            elif days <= 15:
                category = ExpiryNotification.AlertCategory.URGENT_15
                category_label = f"URGENT: Expiring in {days} days (<= 15 Days)"
                summary['urgent_15'] += 1
            elif days <= 30:
                category = ExpiryNotification.AlertCategory.WARNING_30
                category_label = f"NOTICE: Expiring in {days} days (<= 30 Days)"
                summary['warning_30'] += 1
            else:
                # Still safe (> 30 days)
                continue

            # Check for deduplication: has a notification for this batch and this alert_category already been recorded?
            already_notified = ExpiryNotification.objects.filter(
                batch=batch,
                alert_category=category
            ).exists()

            if already_notified:
                summary['duplicates_skipped'] += 1
                continue

            # Construct email alert
            medicine = batch.medicine
            subject = f"[Pharmacy Alert: {category_label}] {medicine.name} (Batch #{batch.batch_number})"
            body = (
                f"SMART MEDICINE INVENTORY - EXPIRY NOTIFICATION\n"
                f"{'=' * 60}\n\n"
                f"Alert Level:       {category_label}\n"
                f"Medicine Name:     {medicine.name}\n"
                f"Generic Name:      {medicine.generic_name}\n"
                f"Medicine ID:       {medicine.medicine_id}\n"
                f"Category:          {medicine.category.name}\n"
                f"Batch Number:      {batch.batch_number}\n"
                f"Remaining Stock:   {batch.available_quantity} units\n"
                f"Expiry Date:       {batch.expiry_date.strftime('%B %d, %Y')}\n"
                f"Days to Expiry:    {days} days\n"
                f"Supplier:          {batch.supplier.company_name} ({batch.supplier.contact_number})\n\n"
                f"Action Recommended:\n"
                f"- If expired: Quarantined & record expired stock disposal immediately.\n"
                f"- If critical/urgent: Prioritize dispensing (FEFO) or return to supplier if eligible.\n\n"
                f"Log into the Smart Pharmacy Inventory System to manage this batch.\n"
                f"Timestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            )

            status = ExpiryNotification.Status.SENT
            error_msg = None

            if send_emails:
                try:
                    send_mail(
                        subject=subject,
                        message=body,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'alerts@smartpharmacy.local'),
                        recipient_list=recipients,
                        fail_silently=False
                    )
                    summary['emails_sent'] += 1
                except Exception as ex:
                    logger.warning(f"Email dispatch warning: {ex}")
                    status = ExpiryNotification.Status.FAILED
                    error_msg = str(ex)

            # Record notification in database
            recipient_display = ", ".join(recipients) if len(recipients) <= 2 else f"{recipients[0]} (+{len(recipients)-1} more)"
            notification = ExpiryNotification.objects.create(
                batch=batch,
                alert_category=category,
                recipient_email=recipient_display,
                subject=subject,
                message_body=body,
                status=status,
                error_message=error_msg,
                is_read=False
            )

            summary['new_notifications_created'] += 1
            summary['details'].append({
                'medicine': medicine.name,
                'batch': batch.batch_number,
                'category': category,
                'days': days,
                'status': status
            })

        return summary
