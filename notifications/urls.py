from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list_view, name='notification_list'),
    path('trigger-scan/', views.trigger_scan_view, name='trigger_expiry_scan'),
    path('<int:pk>/mark-read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('mark-all-read/', views.mark_all_read_view, name='mark_all_notifications_read'),
]
