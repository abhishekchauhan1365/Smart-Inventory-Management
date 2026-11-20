from django.db import models
from django.conf import settings
from inventory.models import MedicineBatch


class ExpiryNotification(models.Model):
    class AlertCategory(models.TextChoices):
        EXPIRED = 'EXPIRED', 'Already Expired'
        CRITICAL_7 = 'CRITICAL_7', 'Expiring within 7 Days'
        URGENT_15 = 'URGENT_15', 'Expiring within 15 Days'
        WARNING_30 = 'WARNING_30', 'Expiring within 30 Days'

    class Status(models.TextChoices):
        SENT = 'SENT', 'Sent Successfully'
        FAILED = 'FAILED', 'Delivery Failed'
        READ = 'READ', 'Read by Staff'

    batch = models.ForeignKey(
        MedicineBatch,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    alert_category = models.CharField(
        max_length=20,
        choices=AlertCategory.choices
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    message_body = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SENT
    )
    is_read = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    notification_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Expiry Notification'
        verbose_name_plural = 'Expiry Notifications'

    def __str__(self):
        return f"[{self.get_alert_category_display()}] {self.batch.medicine.name} (Batch: {self.batch.batch_number}) -> {self.recipient_email}"

    @property
    def badge_class(self):
        if self.alert_category == 'EXPIRED':
            return 'bg-danger text-white'
        elif self.alert_category == 'CRITICAL_7':
            return 'bg-danger text-white'
        elif self.alert_category == 'URGENT_15':
            return 'bg-warning text-dark'
        return 'bg-info text-dark'
