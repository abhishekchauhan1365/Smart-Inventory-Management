from django.contrib import admin
from .models import ExpiryNotification


@admin.register(ExpiryNotification)
class ExpiryNotificationAdmin(admin.ModelAdmin):
    list_display = ('batch', 'alert_category', 'recipient_email', 'status', 'is_read', 'sent_at')
    list_filter = ('alert_category', 'status', 'is_read', 'sent_at')
    search_fields = ('batch__batch_number', 'batch__medicine__name', 'recipient_email', 'subject')
    readonly_fields = ('sent_at', 'notification_date')
