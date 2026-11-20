from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('medicines/', views.medicine_list_view, name='medicine_list'),
    path('medicines/add/', views.medicine_create_view, name='medicine_create'),
    path('medicines/<int:pk>/', views.medicine_detail_view, name='medicine_detail'),
    path('medicines/<int:pk>/edit/', views.medicine_update_view, name='medicine_update'),
    path('medicines/<int:pk>/delete/', views.medicine_delete_view, name='medicine_delete'),
    path('medicines/<int:pk>/dispense/', views.stock_dispense_view, name='stock_dispense'),

    # Batches
    path('batches/', views.batch_list_view, name='batch_list'),
    path('batches/add/', views.batch_create_view, name='batch_create'),
    path('batches/<int:pk>/', views.batch_detail_view, name='batch_detail'),
    path('batches/<int:pk>/edit/', views.batch_update_view, name='batch_update'),
    path('batches/<int:pk>/dispose/', views.batch_dispose_view, name='batch_dispose'),

    # Stock Adjustment & Audit
    path('stock/adjustment/', views.stock_adjustment_view, name='stock_adjustment'),
    path('stock/transactions/', views.transaction_list_view, name='transaction_list'),

    # Categories
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/add/', views.category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update_view, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete_view, name='category_delete'),
]
