from django.core.management.base import BaseCommand
from notifications.services import ExpiryAlertService


class Command(BaseCommand):
    help = 'Scan medicine batches and dispatch automated email expiry warnings to authorized staff'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-email',
            action='store_true',
            help='Run scan and record database notifications without sending emails',
        )

    def handle(self, *args, **options):
        send_emails = not options['no_email']
        self.stdout.write(self.style.NOTICE("Initiating automated medicine expiry scan..."))

        summary = ExpiryAlertService.run_expiry_check(send_emails=send_emails)

        self.stdout.write(self.style.SUCCESS(
            f"Expiry check completed successfully!\n"
            f"- Scanned Batches:           {summary['scanned_batches']}\n"
            f"- Already Expired:            {summary['already_expired']}\n"
            f"- Critical (<= 7 days):       {summary['critical_7']}\n"
            f"- Urgent (<= 15 days):        {summary['urgent_15']}\n"
            f"- Notice (<= 30 days):        {summary['warning_30']}\n"
            f"- New Alerts Created:         {summary['new_notifications_created']}\n"
            f"- Emails Dispatched:          {summary['emails_sent']}\n"
            f"- Duplicate Alerts Skipped:   {summary['duplicates_skipped']}"
        ))
