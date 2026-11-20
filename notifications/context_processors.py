from datetime import date, timedelta


def alert_badges_processor(request):
    """
    Context processor providing real-time notification and stock alert metrics
    for navigation badges, top bars, and alerts across the pharmacy system.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        from inventory.models import Medicine, MedicineBatch
        from notifications.models import ExpiryNotification

        today = date.today()
        day7 = today + timedelta(days=7)
        day15 = today + timedelta(days=15)
        day30 = today + timedelta(days=30)

        # Active batches on shelf with available quantity
        active_batches = MedicineBatch.objects.filter(available_quantity__gt=0)

        expired_count = active_batches.filter(expiry_date__lt=today).count()
        critical_7_count = active_batches.filter(expiry_date__gte=today, expiry_date__lte=day7).count()
        urgent_15_count = active_batches.filter(expiry_date__gt=day7, expiry_date__lte=day15).count()
        warning_30_count = active_batches.filter(expiry_date__gt=day15, expiry_date__lte=day30).count()
        total_near_expiry_count = critical_7_count + urgent_15_count + warning_30_count

        # Low stock medicines count
        low_stock_count = 0
        for med in Medicine.objects.filter(is_active=True):
            if med.is_low_stock:
                low_stock_count += 1

        unread_notifications = ExpiryNotification.objects.filter(is_read=False).count()
        recent_notifications = ExpiryNotification.objects.select_related('batch', 'batch__medicine')[:5]

        return {
            'global_expired_count': expired_count,
            'global_critical_7_count': critical_7_count,
            'global_urgent_15_count': urgent_15_count,
            'global_warning_30_count': warning_30_count,
            'global_near_expiry_count': total_near_expiry_count,
            'global_low_stock_count': low_stock_count,
            'global_unread_notifications_count': unread_notifications,
            'global_recent_notifications': recent_notifications,
        }
    except Exception:
        # In case tables aren't migrated yet during setup
        return {
            'global_expired_count': 0,
            'global_critical_7_count': 0,
            'global_urgent_15_count': 0,
            'global_warning_30_count': 0,
            'global_near_expiry_count': 0,
            'global_low_stock_count': 0,
            'global_unread_notifications_count': 0,
            'global_recent_notifications': [],
        }
