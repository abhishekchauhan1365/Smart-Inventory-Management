from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_index_view, name='reports_index'),
    path('inventory/', views.report_inventory_view, name='report_inventory'),
    path('expired/', views.report_expired_view, name='report_expired'),
    path('near-expiry/', views.report_near_expiry_view, name='report_near_expiry'),
    path('low-stock/', views.report_low_stock_view, name='report_low_stock'),
    path('suppliers/', views.report_suppliers_view, name='report_suppliers'),
    path('stock-movement/', views.report_stock_movement_view, name='report_stock_movement'),
]
