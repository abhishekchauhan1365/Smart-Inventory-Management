from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from accounts.decorators import staff_or_admin_required
from .models import ExpiryNotification
from .services import ExpiryAlertService


@staff_or_admin_required
def notification_list_view(request):
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')

    notifications = ExpiryNotification.objects.select_related(
        'batch', 'batch__medicine', 'batch__supplier'
    )

    if category_filter:
        notifications = notifications.filter(alert_category=category_filter)

    if status_filter == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status_filter == 'read':
        notifications = notifications.filter(is_read=True)

    notifications = notifications.order_by('-sent_at')

    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'notifications/notification_list.html', {
        'page_obj': page_obj,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'categories': ExpiryNotification.AlertCategory.choices,
        'total_count': notifications.count(),
    })


@staff_or_admin_required
def trigger_scan_view(request):
    """
    On-demand button trigger to scan inventory for nearing/expired batches,
    dispatch emails, and prevent duplicate notifications.
    """
    if request.method == 'POST':
        summary = ExpiryAlertService.run_expiry_check(send_emails=True)
        messages.success(
            request,
            f"Expiry scan complete! Scanned {summary['scanned_batches']} active batches. "
            f"Found: {summary['already_expired']} expired, {summary['critical_7']} critical (<=7d), "
            f"{summary['urgent_15']} urgent (<=15d), {summary['warning_30']} notice (<=30d). "
            f"Created {summary['new_notifications_created']} new alert notifications ({summary['duplicates_skipped']} duplicates skipped)."
        )
    return redirect('notification_list')


@staff_or_admin_required
def mark_notification_read_view(request, pk):
    notification = get_object_or_404(ExpiryNotification, pk=pk)
    notification.is_read = True
    notification.save()
    messages.success(request, f"Alert for '{notification.batch.medicine.name}' marked as read.")
    return redirect(request.META.get('HTTP_REFERER', 'notification_list'))


@staff_or_admin_required
def mark_all_read_view(request):
    if request.method == 'POST':
        count = ExpiryNotification.objects.filter(is_read=False).update(is_read=True)
        messages.success(request, f"Marked {count} notifications as read.")
    return redirect('notification_list')
